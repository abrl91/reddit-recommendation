#!/bin/bash
# Bootstrap script for Airflow EC2 instance
# Runs once on first boot as root
#
# Logs: /var/log/cloud-init-output.log

set -ex  # Exit on error, print commands

echo "=== Starting bootstrap at $(date) ==="

# Update system packages
dnf update -y

# Install Docker
dnf install -y docker
systemctl enable docker
systemctl start docker

# Install Docker Compose (v2 plugin)
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# Verify installations
docker --version
docker compose version

# Install git
dnf install -y git

# Create app directory
mkdir -p /opt/reddit-recommendation
cd /opt/reddit-recommendation

# Clone the repository
git clone ${github_repo} .

# Create airflow directories
mkdir -p airflow/logs
mkdir -p airflow/dags

# Create .env.prod from example (user will need to edit secrets)
if [ -f airflow/.env.prod.example ]; then
  cp airflow/.env.prod.example airflow/.env.prod
  echo "Created .env.prod from example - REMEMBER TO EDIT SECRETS!"
fi

# Create systemd service for Airflow
cat > /etc/systemd/system/airflow.service << 'EOF'
[Unit]
Description=Airflow Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/reddit-recommendation/airflow
ExecStart=/usr/local/lib/docker/cli-plugins/docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml up -d
ExecStop=/usr/local/lib/docker/cli-plugins/docker-compose -f docker-compose.yaml -f docker-compose.prod.yaml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd to recognize new service
systemctl daemon-reload

# Add ec2-user to docker group (so they can run docker without sudo)
usermod -aG docker ec2-user

echo "=== Bootstrap complete at $(date) ==="
echo "Next steps:"
echo "1. SSH to instance"
echo "2. Edit /opt/reddit-recommendation/airflow/.env.prod with secrets"
echo "3. Run: sudo systemctl enable airflow && sudo systemctl start airflow"
echo "4. Access Airflow at http://<ELASTIC_IP>:8080"
