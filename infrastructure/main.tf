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
  vpc_security_group_ids = [aws_security_group.brb_app_sg.id]
  subnet_id              = data.aws_subnets.default.ids[0]
  
  # Use IAM Instance Profile for SSM access
  iam_instance_profile = aws_iam_instance_profile.brb_app.name

  root_block_device {
    volume_type = "gp2"
    volume_size = 8
    encrypted   = true
  }

  monitoring = false

  user_data_base64 = base64encode(templatefile("${path.module}/user-data.sh", {
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
}

# IAM Role for EC2 instance to use SSM Session Manager
resource "aws_iam_role" "brb_app" {
  name = "brb-app-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "brb-app-ec2-role"
    Environment = "production"
  }
}

# IAM Instance Profile
resource "aws_iam_instance_profile" "brb_app" {
  name = "brb-app-ec2-profile"
  role = aws_iam_role.brb_app.name
}

# IAM Policy for SSM Session Manager
resource "aws_iam_role_policy_attachment" "ssm_managed_instance" {
  role       = aws_iam_role.brb_app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# Route53 record already exists - skip creation
# The record brb.elvisquant.com already points to your EC2 instance

output "ec2_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.brb_app.public_ip
}

output "application_url" {
  description = "URL where the application will be available"
  value       = "https://brb.elvisquant.com"
}