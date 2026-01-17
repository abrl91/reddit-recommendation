# Terraform configuration for Lemmy Recommendation Airflow deployment

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # State stored locally (for learning)
  # In production, you'd use S3 backend for team collaboration
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "lemmy-recommendation"
      Environment = "production"
      ManagedBy   = "terraform"
    }
  }
}
