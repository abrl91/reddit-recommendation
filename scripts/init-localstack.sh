#!/bin/bash
# Create S3 buckets for LocalStack

awslocal s3 mb s3://lemmy-bronze-data
awslocal s3 mb s3://lemmy-silver-data
awslocal s3 mb s3://lemmy-gold-data

echo "LocalStack S3 buckets created!"
