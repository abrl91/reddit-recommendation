# Security Group - Firewall rules for EC2
#
# Allows:
# - SSH (port 22) from your IP only
# - Airflow UI (port 8080) from your IP only
# - All outbound traffic (for pip, docker pull, etc.)

resource "aws_security_group" "airflow" {
  name        = "reddit-recommendation-airflow-sg"
  description = "Security group for Airflow EC2 instance"
  vpc_id      = aws_vpc.main.id

  # SSH access from your IP only
  ingress {
    description = "SSH from allowed IP"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  # Airflow UI access from your IP only
  ingress {
    description = "Airflow UI from allowed IP"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ip]
  }

  # Allow all outbound traffic
  # Needed for: apt/dnf updates, docker pull, git clone, S3 access
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "reddit-recommendation-airflow-sg"
  }
}
