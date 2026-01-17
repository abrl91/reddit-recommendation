# IAM Role for EC2 to access S3
#
# This allows the EC2 instance to read/write to S3 buckets
# WITHOUT storing any credentials on the machine.
# Much more secure than access keys!

# Trust policy - allows EC2 service to assume this role
data "aws_iam_policy_document" "ec2_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

# The IAM role itself
resource "aws_iam_role" "airflow" {
  name               = "lemmy-recommendation-airflow-role"
  assume_role_policy = data.aws_iam_policy_document.ec2_assume_role.json

  tags = {
    Name = "lemmy-recommendation-airflow-role"
  }
}

# Permission policy - what the role can do (S3 access)
data "aws_iam_policy_document" "s3_access" {
  # List buckets (needed for s3fs)
  statement {
    actions = ["s3:ListBucket"]
    resources = [
      "arn:aws:s3:::${var.s3_bucket_bronze}",
      "arn:aws:s3:::${var.s3_bucket_silver}",
      "arn:aws:s3:::${var.s3_bucket_gold}",
    ]
  }

  # Read/Write objects in buckets
  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
    ]
    resources = [
      "arn:aws:s3:::${var.s3_bucket_bronze}/*",
      "arn:aws:s3:::${var.s3_bucket_silver}/*",
      "arn:aws:s3:::${var.s3_bucket_gold}/*",
    ]
  }
}

# Attach the permission policy to the role
resource "aws_iam_role_policy" "s3_access" {
  name   = "lemmy-recommendation-s3-access"
  role   = aws_iam_role.airflow.id
  policy = data.aws_iam_policy_document.s3_access.json
}

# Instance profile - required to attach IAM role to EC2
# (You can't attach a role directly; you need this wrapper)
resource "aws_iam_instance_profile" "airflow" {
  name = "lemmy-recommendation-airflow-profile"
  role = aws_iam_role.airflow.name
}
