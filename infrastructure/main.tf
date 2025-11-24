# Terraform configuration
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "brb-app-tf-state-free"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "brb-app-tf-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = "us-east-1"
}

# S3 Bucket for Terraform state (free for 5GB)
resource "aws_s3_bucket" "tf_state" {
  bucket = "brb-app-tf-state-free"

  tags = {
    Name        = "BRB App Terraform State"
    Environment = "production"
    CostCenter  = "free-tier"
  }
}

resource "aws_s3_bucket_versioning" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "tf_state" {
  bucket = aws_s3_bucket.tf_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# DynamoDB for state locking (free - 25 WCU/RCU)
resource "aws_dynamodb_table" "tf_locks" {
  name         = "brb-app-tf-locks"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "BRB App Terraform Locks"
    Environment = "production"
    CostCenter  = "free-tier"
  }
}

# Get the default VPC and subnets (free)
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group (free)
resource "aws_security_group" "brb_app_sg" {
  name        = "brb-app-sg"
  description = "Security group for BRB application"
  vpc_id      = data.aws_vpc.default.id

  # SSH access from anywhere
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  # HTTP access
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  # HTTPS access
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

  # Outbound internet access
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Internet access"
  }

  tags = {
    Name        = "brb-app-sg"
    Environment = "production"
    CostCenter  = "free-tier"
  }
}

# Get the latest Amazon Linux 2023 AMI (free tier eligible)
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# Free tier EC2 instance - t2.micro (750 hours free per month)
resource "aws_instance" "brb_app" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t2.micro"  # Free tier eligible
  vpc_security_group_ids = [aws_security_group.brb_app_sg.id]
  subnet_id              = data.aws_subnets.default.ids[0]
  key_name               = aws_key_pair.brb_key.key_name

  # Free tier EBS volume - 8GB gp2 (well within 30GB free tier)
  root_block_device {
    volume_type = "gp2"
    volume_size = 8
    encrypted   = true
  }

  # Disable detailed monitoring (basic monitoring is free)
  monitoring = false

  user_data = base64encode(templatefile("${path.module}/user-data.sh", {
    domain          = "brb.elvisquant.com"
    docker_username = var.docker_username
    docker_password = var.docker_password
    db_password     = var.db_password
    secret_key      = var.secret_key
  }))

  tags = {
    Name        = "brb-app-server"
    Environment = "production"
    CostCenter  = "free-tier"
    Project     = "brb-app"
  }

  depends_on = [
    aws_security_group.brb_app_sg,
    aws_key_pair.brb_key
  ]
}

# SSH key pair (free)
resource "aws_key_pair" "brb_key" {
  key_name   = "brb-app-key"
  public_key = var.ssh_public_key

  tags = {
    Name        = "brb-app-key"
    Environment = "production"
    CostCenter  = "free-tier"
  }
}

# Get the Route53 hosted zone for elvisquant.com
data "aws_route53_zone" "elvisquant" {
  name         = "elvisquant.com."
  private_zone = false
}

# Route53 A record for brb.elvisquant.com
resource "aws_route53_record" "brb_app" {
  zone_id = data.aws_route53_zone.elvisquant.zone_id
  name    = "brb.${data.aws_route53_zone.elvisquant.name}"
  type    = "A"
  ttl     = 300
  records = [aws_instance.brb_app.public_ip]

  tags = {
    Name        = "brb-app-dns"
    Environment = "production"
    CostCenter  = "free-tier"
  }

  depends_on = [aws_instance.brb_app]
}

# CloudWatch basic monitoring (free)
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "brb-app-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "120"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "Monitor EC2 CPU utilization - free tier monitoring"
  alarm_actions       = []  # No SNS to avoid costs

  dimensions = {
    InstanceId = aws_instance.brb_app.id
  }

  tags = {
    Name        = "brb-app-cpu-alarm"
    Environment = "production"
    CostCenter  = "free-tier"
  }
}