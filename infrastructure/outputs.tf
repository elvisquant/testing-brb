output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.brb_app.public_ip
}

output "application_url" {
  description = "URL where the application will be available"
  value       = "https://brb.elvisquant.com"
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for Terraform state"
  value       = data.aws_s3_bucket.tf_state.bucket
}

output "dynamodb_table" {
  description = "Name of the DynamoDB table for state locking"
  value       = data.aws_dynamodb_table.tf_locks.name
}