from datetime import datetime
from typing import Optional, Callable, Dict, Set
import threading
from collections import deque


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from croniter import croniter

from models import db, Job, JobLog
from executors import get_executor


class SchedulerService:
    """Service for managing job scheduling with APScheduler."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern to ensure only one scheduler instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.scheduler = BackgroundScheduler()
        self.socketio = None
        self.app = None
        
        # Queuing state
        self._job_queues: Dict[int, deque] = {}  # job_id -> deque of (log_id, trigger_type)
        self._running_jobs: Set[int] = set()     # set of currently running job_ids
        self._queue_lock = threading.Lock()
        
        self._initialized = True
    
    def init_app(self, app, socketio, cleanup=True):
        """Initialize with Flask app and SocketIO instance."""
        self.app = app
        self.socketio = socketio
        
        # Start scheduler
        if not self.scheduler.running:
            self.scheduler.start()
        
        # Load existing jobs from database
        with app.app_context():
            if cleanup:
                self._cleanup_stale_jobs()
            self._load_jobs_from_db()
    
    def _cleanup_stale_jobs(self):
        """Mark any jobs that were 'running' during restart as 'failed'."""
        try:
            # Find running logs
            stale_logs = JobLog.query.filter_by(status='running').all()
            for log in stale_logs:
                log.status = 'failed'
                log.finished_at = datetime.utcnow()
                log.error_output = (log.error_output or '') + '\n[SYSTEM] Job marked as failed due to server restart.'
                log.exit_code = -1
            
            # Find running jobs
            stale_jobs = Job.query.filter_by(status='running').all()
            for job in stale_jobs:
                job.status = 'failed'
            
            if stale_logs or stale_jobs:
                db.session.commit()
                print(f"[SYSTEM] Cleaned up {len(stale_logs)} stale logs and {len(stale_jobs)} stale jobs.")
                
        except Exception as e:
            print(f"Error cleaning up stale jobs: {e}")

    def _load_jobs_from_db(self):
        """Load all enabled jobs from database and schedule them."""
        jobs = Job.query.filter_by(enabled=True).all()
        for job in jobs:
            self._add_job_to_scheduler(job)
    
    def _add_job_to_scheduler(self, job: Job):
        """Add a job to the APScheduler."""
        job_id = f"job_{job.id}"
        
        # Remove existing job if present
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        if not job.enabled:
            return
        
        # Create trigger based on schedule type
        trigger = self._create_trigger(job)
        if not trigger:
            return
        
        # Add job to scheduler
        self.scheduler.add_job(
            func=self._execute_job_scheduled,
            trigger=trigger,
            args=[job.id],
            id=job_id,
            name=job.name,
            replace_existing=True
        )
        
        # Update next run time
        with self.app.app_context():
            job_record = db.session.get(Job, job.id)
            if job_record:
                next_run = self.scheduler.get_job(job_id)
                if next_run and next_run.next_run_time:
                    job_record.next_run = next_run.next_run_time
                    db.session.commit()
    
    def _create_trigger(self, job: Job):
        """Create APScheduler trigger from job schedule settings."""
        try:
            if job.schedule_type == 'cron' and job.cron_expression:
                # Parse cron expression
                parts = job.cron_expression.split()
                if len(parts) == 5:
                    return CronTrigger(
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2],
                        month=parts[3],
                        day_of_week=parts[4]
                    )
                elif len(parts) == 6:
                    return CronTrigger(
                        second=parts[0],
                        minute=parts[1],
                        hour=parts[2],
                        day=parts[3],
                        month=parts[4],
                        day_of_week=parts[5]
                    )
            elif job.schedule_type == 'interval' and job.interval_seconds:
                return IntervalTrigger(seconds=job.interval_seconds)
            elif job.schedule_type == 'once' and job.run_at:
                if job.run_at > datetime.utcnow():
                    return DateTrigger(run_date=job.run_at)
        except Exception as e:
            print(f"Error creating trigger for job {job.id}: {e}")
        
        return None
    
    def _emit_log(self, job_id: int, log_id: int, message: str):
        """Emit log message via SocketIO."""
        if self.socketio:
            self.socketio.emit('job_log', {
                'job_id': job_id,
                'log_id': log_id,
                'message': message,
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/jobs', room=f'job_{job_id}')
            self.socketio.sleep(0)  # Force yield to allow flush
    
    def _emit_job_update(self, job_id: int, status: str, last_run: datetime = None, next_run: datetime = None):
        """Emit job status update event."""
        if self.socketio:
            data = {
                'job_id': job_id,
                'status': status,
                'timestamp': datetime.utcnow().isoformat()
            }
            if last_run:
                data['last_run'] = last_run.isoformat()
            if next_run:
                data['next_run'] = next_run.isoformat()
                
            self.socketio.emit('job_update', data, namespace='/jobs')
            self.socketio.sleep(0)  # Force yield to allow flush
            print(f"[DEBUG] Emitted job_update for job {job_id}: {status}")

    def _submit_job(self, job_id: int, trigger_type: str) -> Optional[int]:
        """Submit a job for execution. Returns log_id."""
        with self.app.app_context():
            job = db.session.get(Job, job_id)
            if not job:
                return None
            
            # Create log entry immediately
            job_log = JobLog(
                job_id=job_id,
                started_at=datetime.utcnow(),
                trigger_type=trigger_type,
                status='queued'
            )
            db.session.add(job_log)
            
            is_running = job_id in self._running_jobs
            if not is_running:
                job.status = 'queued'
                self._emit_job_update(job_id, 'queued')
            
            db.session.commit()
            log_id = job_log.id
            
            # Emit queued event
            self._emit_log(job_id, log_id, f"[QUEUED] Job '{job.name}' queued at {datetime.utcnow().isoformat()}")
        
        # Add to queue
        with self._queue_lock:
            if job_id not in self._job_queues:
                self._job_queues[job_id] = deque()
            self._job_queues[job_id].append((log_id, trigger_type))
            
        # Try to process queue
        self._process_queue(job_id)
        
        return log_id
    
    def _process_queue(self, job_id: int):
        """Process the next job in queue if idle."""
        with self._queue_lock:
            # If already running, do nothing
            if job_id in self._running_jobs:
                return
            
            # If queue empty, do nothing
            if job_id not in self._job_queues or not self._job_queues[job_id]:
                if job_id in self._job_queues:
                    del self._job_queues[job_id]
                return
            
            # Pop next job
            log_id, trigger_type = self._job_queues[job_id].popleft()
            self._running_jobs.add(job_id)
            
        # Spawn worker thread
        thread = threading.Thread(
            target=self._run_job_worker,
            args=[job_id, log_id]
        )
        thread.start()

    def _execute_job_scheduled(self, job_id: int):
        """APScheduler callback."""
        self._submit_job(job_id, 'scheduled')

    def run_job_now(self, job_id: int) -> Optional[int]:
        """Manually trigger a job execution. Returns log_id."""
        return self._submit_job(job_id, 'manual')
    def _run_job_worker(self, job_id: int, log_id: int):
        """Worker executing the job."""
        try:
            with self.app.app_context():
                job = db.session.get(Job, job_id)
                job_log = db.session.get(JobLog, log_id)
                
                if not job or not job_log:
                    return
                
                # Update status to running
                job.status = 'running'
                job_log.status = 'running'
                job.last_run = datetime.utcnow()
                db.session.commit()
                
                self._emit_job_update(job_id, 'running', last_run=job.last_run)
                
                # Emit start event
                self._emit_log(job_id, log_id, f"[START] Job '{job.name}' started at {datetime.utcnow().isoformat()}")
                
                # Get credential if needed
                credential = job.credential if job.credential_id else None
                
                # Get executor
                try:
                    executor = get_executor(job.job_type)
                except ValueError as e:
                    self._finish_job(job, job_log, False, -1, str(e), "")
                    return
                
                # Create log callback
                output_buffer = []
                def log_callback(message: str):
                    output_buffer.append(message)
                    self._emit_log(job_id, log_id, message)
                
                # Execute
                try:
                    result = executor.execute(job, credential, log_callback)
                    self._finish_job(
                        job, job_log,
                        result.success,
                        result.exit_code,
                        result.output or '\n'.join(output_buffer),
                        result.error_output
                    )
                except Exception as e:
                    self._finish_job(job, job_log, False, -1, '\n'.join(output_buffer), str(e))
        
        except Exception as e:
            print(f"Error in job worker: {e}")
        finally:
            # Cleanup and check queue for next item
            with self._queue_lock:
                if job_id in self._running_jobs:
                    self._running_jobs.remove(job_id)
            
            # Trigger next item in queue
            self._process_queue(job_id)

    def _finish_job(self, job: Job, job_log: JobLog, success: bool, exit_code: int, output: str, error_output: str):
        """Finalize job execution and update records."""
        job_log.finished_at = datetime.utcnow()
        job_log.status = 'success' if success else 'failed'
        job_log.exit_code = exit_code
        job_log.output = output
        job_log.error_output = error_output
        
        job.status = 'success' if success else 'failed'
        
        # Update next run time
        scheduler_job = self.scheduler.get_job(f"job_{job.id}")
        if scheduler_job and scheduler_job.next_run_time:
            job.next_run = scheduler_job.next_run_time
        
        db.session.commit()
        
        self._emit_job_update(job.id, job.status, next_run=job.next_run)
        
        # Emit completion event
        self._emit_log(
            job.id, job_log.id,
            f"[END] Job finished with status: {'SUCCESS' if success else 'FAILED'} (exit code: {exit_code})"
        )
        self._emit_job_complete(job.id, job_log.id, success)
    
    def _emit_job_complete(self, job_id: int, log_id: int, success: bool):
        """Emit job completion event."""
        if self.socketio:
            self.socketio.emit('job_complete', {
                'job_id': job_id,
                'log_id': log_id,
                'success': success,
                'timestamp': datetime.utcnow().isoformat()
            }, namespace='/jobs')
    
    def add_job(self, job: Job):
        """Add or update a job in the scheduler."""
        self._add_job_to_scheduler(job)
    
    def remove_job(self, job_id: int):
        """Remove a job from the scheduler."""
        scheduler_job_id = f"job_{job_id}"
        if self.scheduler.get_job(scheduler_job_id):
            self.scheduler.remove_job(scheduler_job_id)
    
    def pause_job(self, job_id: int):
        """Pause a scheduled job."""
        scheduler_job_id = f"job_{job_id}"
        job = self.scheduler.get_job(scheduler_job_id)
        if job:
            job.pause()
    
    def resume_job(self, job_id: int):
        """Resume a paused job."""
        scheduler_job_id = f"job_{job_id}"
        job = self.scheduler.get_job(scheduler_job_id)
        if job:
            job.resume()
    
    def get_next_run_time(self, cron_expression: str) -> Optional[datetime]:
        """Calculate next run time from cron expression."""
        try:
            cron = croniter(cron_expression, datetime.utcnow())
            return cron.get_next(datetime)
        except Exception:
            return None
    
    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()


# Singleton instance
scheduler_service = SchedulerService()
