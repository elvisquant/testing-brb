output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.brb_app.public_ip
}

output "application_url" {
  description = "URL where the application will be available"
  value       = "https://brb.elvisquant.com"
}

output "route53_status" {
  description = "Status of Route53 DNS configuration"
  value       = "✅ Subdomain brb.elvisquant.com automatically configured in Route53"
}

output "dns_propagation_info" {
  description = "Information about DNS propagation"
  value = <<EOT

🌐 DNS AUTOMATION COMPLETE:

✅ Route53 record created: brb.elvisquant.com → ${aws_instance.brb_app.public_ip}
⏳ DNS propagation may take 2-5 minutes
🔗 Your app will be available at: https://brb.elvisquant.com

You can also access via IP directly: http://${aws_instance.brb_app.public_ip}
EOT
}

output "ssh_connection_command" {
  description = "Command to SSH into the instance for debugging"
  value       = "ssh -i brb-app-key ec2-user@${aws_instance.brb_app.public_ip}"
}

output "free_tier_resources" {
  description = "List of free tier resources being used"
  value = [
    "EC2 t2.micro instance (750 hrs/month free)",
    "EBS gp2 volume 8GB (30GB free)",
    "S3 storage (5GB free)",
    "DynamoDB (25 WCU/RCU free)",
    "CloudWatch basic monitoring (free)",
    "Security Groups (free)",
    "Route53 hosted zone (already exists)",
    "Route53 record (~$0.50/month)",
    "Data Transfer (100GB free out)"
  ]
}

output "estimated_monthly_cost" {
  description = "Estimated monthly cost"
  value       = "~$0.50 (only Route53 record costs, everything else is free tier)"
}