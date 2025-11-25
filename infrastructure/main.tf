provider "aws" {
  region = "us-east-1"
}

# Import existing S3 bucket
data "aws_s3_bucket" "tf_state" {
  bucket = "brb-app-tf-state-2024"
}

# Import existing DynamoDB table
data "aws_dynamodb_table" "tf_locks" {
  name = "brb-app-tf-locks"
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

# Get the latest Ubuntu 22.04 LTS AMI (Free Tier eligible)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical's official AWS account ID

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# --- THIS IS THE CHANGE ---
# Find the existing key pair named "devops" in your AWS account.
data "aws_key_pair" "deployer_key" {
  key_name = "devops" 
}
# --- END OF CHANGE ---

# EC2 Instance
resource "aws_instance" "brb_app" {
  ami = data.aws_ami.ubuntu.id
  
  # Use the Free Tier instance type
  instance_type = "t2.micro"

  vpc_security_group_ids = [aws_security_group.brb_app_sg.id]
  subnet_id              = data.aws_subnets.default.ids[0]
  
  # Associate your existing key pair with the instance
  key_name = data.aws_key_pair.deployer_key.key_name
  
  root_block_device {
    volume_type = "gp2"
    volume_size = 8 # Within Free Tier limits
    encrypted   = true
  }

  monitoring = false

  user_data_base_64 = base64encode(templatefile("${path.module}/user-data.sh", {
    github_repository = "elvisquant/brb-app" # Confirm this is your correct username/repo
    docker_username = var.docker_username
    db_password     = var.db_password
    secret_key      = var.secret_key
  }))

  tags = {
    Name        = "brb-app-server"
    Environment = "production"
  }
}