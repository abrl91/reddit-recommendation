# Input variables for the deployment
# Values are set in terraform.tfvars (gitignored)

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

variable "key_pair_name" {
  description = "Name of the EC2 key pair for SSH access"
  type        = string
}

variable "allowed_ip" {
  description = "Your IP address for SSH and HTTP access (format: x.x.x.x/32)"
  type        = string
}

variable "s3_bucket_bronze" {
  description = "S3 bucket name for bronze layer"
  type        = string
}

variable "s3_bucket_silver" {
  description = "S3 bucket name for silver layer"
  type        = string
}

variable "s3_bucket_gold" {
  description = "S3 bucket name for gold layer"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository URL to clone"
  type        = string
  default     = "https://github.com/yourusername/reddit-recommendation.git"
}

# VPC Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "CIDR block for public subnet"
  type        = string
  default     = "10.0.1.0/24"
}
