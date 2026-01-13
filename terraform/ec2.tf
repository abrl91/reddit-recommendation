# EC2 Instance running Airflow
#
# Uses Amazon Linux 2023 with Docker pre-installed capabilities.
# The user_data script bootstraps everything on first boot.

# Get the latest Amazon Linux 2023 AMI
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# The EC2 instance
resource "aws_instance" "airflow" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.airflow.id]
  iam_instance_profile   = aws_iam_instance_profile.airflow.name

  # 30GB root volume (gp3 is newer and cheaper than gp2)
  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    delete_on_termination = true

    tags = {
      Name = "reddit-recommendation-airflow-volume"
    }
  }

  # Bootstrap script - runs once on first boot
  user_data = templatefile("${path.module}/user_data.sh", {
    github_repo = var.github_repo
  })

  tags = {
    Name = "reddit-recommendation-airflow"
  }

  # Wait for user_data to complete before marking as created
  # (useful but adds time; you can remove if you want faster deploys)
  lifecycle {
    create_before_destroy = true
  }
}

# Elastic IP - stable IP address that survives stop/start
resource "aws_eip" "airflow" {
  instance = aws_instance.airflow.id
  domain   = "vpc"

  tags = {
    Name = "reddit-recommendation-airflow-eip"
  }

  # Make sure the internet gateway exists first
  depends_on = [aws_internet_gateway.main]
}
