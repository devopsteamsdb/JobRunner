# JobRunner

JobRunner is a powerful, Flask-based task scheduler designed to manage and execute automation scripts across your infrastructure. It acts as a central control plane for running Python, Bash, and PowerShell scripts, as well as Ansible playbooks.

## Features

*   **Multi-Language Support**: Execute Python, Bash, and PowerShell scripts natively.
*   **Ansible Integration**: Run Ansible playbooks directly, with support for both inline and file-based inventories.
*   **Remote Execution**: Support for SSH and WinRM for executing commands on remote servers.
*   **Flexible Scheduling**: Schedule jobs using Cron expressions, fixed intervals, or one-time runs.
*   **Real-time Logs**: View live execution logs via WebSocket streaming.
*   **REST API**: Full programmatic control over jobs and execution.
*   **Duplicate Jobs**: Easily clone existing job configurations.

## Tech Stack

*   **Backend**: Flask, Flask-SQLAlchemy, Flask-SocketIO, APScheduler
*   **Database**: SQLite (default)
*   **Asynchronous**: Gevent

## Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/devopsteamsdb/JobRunner.git
    cd JobRunner
    ```

2.  Create a virtual environment:
    ```bash
    python -m venv .venv
    # Windows
    .venv\Scripts\activate
    # Linux/Mac
    source .venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

4.  Run the application:
    ```bash
    python app.py
    ```

5.  Access the dashboard at `http://localhost:5000`.

## Configuration

Environment variables can be set in a `.env` file:

*   `SECRET_KEY`: Flask secret key.
*   `DATABASE_URL`: Database connection string (default: `sqlite:///scheduler.db`).
*   `SCHEDULER_TIMEZONE`: Timezone for the scheduler (default: `UTC`).

## License

[MIT](LICENSE)
