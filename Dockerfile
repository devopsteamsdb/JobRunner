# explicitly use Debian 12 (Bookworm) to ensure package availability
FROM python:3.11-slim-bookworm

# Prevent Python from writing pyc files and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Step 1: Install system dependencies
# - libicu72, libssl3, libunwind8: Core dependencies for PowerShell on Debian 12
# - sshpass, openssh-client: Required for Ansible SSH connections
# - git, wget: Build and fetch tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    libicu72 \
    libssl3 \
    libunwind8 \
    sshpass \
    openssh-client \
    git \
    && rm -rf /var/lib/apt/lists/*

# Step 2: Install PowerShell (Manual Binary Install)
# We use the LTS version 7.4.6 which is stable and compatible with these libraries.
# This avoids "apt-get install powershell" repository errors.
RUN wget -q -O powershell.tar.gz https://github.com/PowerShell/PowerShell/releases/download/v7.4.6/powershell-7.4.6-linux-x64.tar.gz \
    && mkdir -p /opt/microsoft/powershell/7 \
    && tar zxf powershell.tar.gz -C /opt/microsoft/powershell/7 \
    && chmod +x /opt/microsoft/powershell/7/pwsh \
    && ln -s /opt/microsoft/powershell/7/pwsh /usr/bin/pwsh \
    && rm powershell.tar.gz

# Step 3: Install Python dependencies
COPY requirements.txt .
# We install ansible here to keep it isolated from system packages
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir ansible

# Step 4: Configure Ansible
# Copy config to /etc/ansible/ansible.cfg so it's not in the world-writable /app volume
# and has correct permissions.
RUN mkdir -p /etc/ansible
COPY ansible.cfg /etc/ansible/ansible.cfg
RUN chmod 644 /etc/ansible/ansible.cfg

# Environment variables to silence warnings
ENV ANSIBLE_DEPRECATION_WARNINGS=False
ENV ANSIBLE_CONFIG=/etc/ansible/ansible.cfg

# Step 5: Copy application code
COPY . .

# Expose port and define entrypoint
EXPOSE 5000
CMD ["python", "app.py"]
