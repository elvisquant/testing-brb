# Terraform configuration
terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

# Create S3 bucket for Terraform state FIRST
resource "aws_s3_bucket" "tf_state" {
  bucket = "brb-app-tf-state-2024"

  tags = {
    Name        = "BRB App Terraform State"
    Environment = "production"
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

# Create DynamoDB table for state locking
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
  }
}

# Get the default VPC and subnets
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group
resource "aws_security_group" "brb_app_sg" {
  name        = "brb-app-sg"
  description = "Security group for BRB application"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

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
  }
}

# Get the latest Amazon Linux 2023 AMI
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

# EC2 Instance
resource "aws_instance" "brb_app" {
  ami                    = data.aws_ami.amazon_linux_2023.id
  instance_type          = "t2.micro"
  vpc_security_group_ids = [aws_security_group.brb_app.sg.id]
  subnet_id              = data.aws_subnets.default.ids[0]
  key_name               = aws_key_pair.brb_key.key_name

  root_block_device {
    volume_type = "gp2"
    volume_size = 8
    encrypted   = true
  }

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
  }

  depends_on = [
    aws_s3_bucket.tf_state,
    aws_dynamodb_table.tf_locks
  ]
}

# SSH key pair
resource "aws_key_pair" "brb_key" {
  key_name   = "brb-app-key"
  public_key = var.ssh_public_key

  tags = {
    Name        = "brb-app-key"
    Environment = "production"
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
  }
}