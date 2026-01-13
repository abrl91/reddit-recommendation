# Output values displayed after terraform apply
# Run `terraform output` anytime to see these again

output "elastic_ip" {
  description = "Elastic IP address (stable across stop/start)"
  value       = aws_eip.airflow.public_ip
}

output "ssh_command" {
  description = "SSH command to connect to the instance"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${aws_eip.airflow.public_ip}"
}

output "airflow_url" {
  description = "Airflow web UI URL"
  value       = "http://${aws_eip.airflow.public_ip}:8080"
}

output "instance_id" {
  description = "EC2 instance ID (for stop/start commands)"
  value       = aws_instance.airflow.id
}

output "stop_instance_command" {
  description = "Command to stop instance (save money)"
  value       = "aws ec2 stop-instances --instance-ids ${aws_instance.airflow.id}"
}

output "start_instance_command" {
  description = "Command to start instance"
  value       = "aws ec2 start-instances --instance-ids ${aws_instance.airflow.id}"
}
