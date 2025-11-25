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

# Security Group - Port 22 must be open for SSH
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

# --- FREE TIER STEP 1: Select a Free Tier eligible AMI ---
# Get the latest Ubuntu 22.04 LTS AMI, which is Free Tier eligible.
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

# Create an EC2 key pair by uploading the public key from the pipeline
resource "aws_key_pair" "deployer_key" {
  key_name   = "brb-app-key"
  public_key = var.ssh_public_key
}

# EC2 Instance
resource "aws_instance" "brb_app" {
  ami = data.aws_ami.ubuntu.id
  
  # --- FREE TIER STEP 2: Select the Free Tier instance type ---
  instance_type = "t2.micro"

  vpc_security_group_ids = [aws_security_group.brb_app_sg.id]
  subnet_id              = data.aws_subnets.default.ids[0]
  
  # Associate the key pair for SSH access
  key_name = aws_key_pair.deployer_key.key_name
  
  root_block_device {
    volume_type = "gp2"
    volume_size = 8 # The free tier includes up to 30GB of EBS storage
    encrypted   = true
  }

  monitoring = false

  user_data_base64 = base64encode(templatefile("${path.module}/user-data.sh", {
    # We pass the repository so user-data can download the docker-compose file
    github_repository = "elvisquant/brb-app" # <-- IMPORTANT: I have put your username/repo here. Confirm it is correct.
    docker_username = var.docker_username
    db_password     = var.db_password
    secret_key      = var.secret_key
  }))

  tags = {
    Name        = "brb-app-server"
    Environment = "production"
  }
}