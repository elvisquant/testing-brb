#!/bin/bash
set -e

# Update system
echo "🔄 Updating system packages..."
sudo yum update -y

# Install Docker
echo "🐳 Installing Docker..."
sudo amazon-linux-extras install docker -y
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
echo "📦 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/download/v2.23.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Create application directory
echo "📁 Setting up application directory..."
sudo mkdir -p /opt/brb-app
cd /opt/brb-app

# Create environment file
echo "🔧 Creating environment configuration..."
sudo cat > .env << EOF
# Database Configuration
DB_NAME=brbdb
DB_USER=brbuser
DB_PASSWORD=${db_password}

# Docker Configuration
DOCKER_REGISTRY=docker.io
BACKEND_IMAGE=${docker_username}/brb-app-backend
IMAGE_TAG=latest

# Application Configuration
SECRET_KEY=${secret_key}
ENVIRONMENT=production
DOMAIN=brb.elvisquant.com

# SSL Configuration
ACME_EMAIL=admin@elvisquant.com

# Version Information
COMMIT_SHA=initial
EOF

# Create directory structure
echo "📂 Creating directory structure..."
sudo mkdir -p traefik

# Create Traefik configuration
echo "🌐 Configuring Traefik..."
sudo cat > traefik/traefik.yml << 'EOF'
api:
  dashboard: false

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

certificatesResolvers:
  myresolver:
    acme:
      email: "admin@elvisquant.com"
      storage: /acme.json
      httpChallenge:
        entryPoint: web

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
EOF

# Create SSL certificate storage
echo "🔐 Setting up SSL certificate storage..."
sudo touch traefik/acme.json
sudo chmod 600 traefik/acme.json

# Set proper ownership
echo "👤 Setting file permissions..."
sudo chown -R ec2-user:ec2-user /opt/brb-app

# Wait for cloud-init to complete
echo "⏳ Waiting for cloud-init to complete..."
sudo cloud-init status --wait

# Start the application
echo "🚀 Starting application services..."
cd /opt/brb-app
sudo -u ec2-user docker-compose -f docker-compose.prod.yml pull || echo "Docker Compose file will be downloaded later"
sudo -u ec2-user docker-compose -f docker-compose.prod.yml up -d || echo "Docker Compose file will be downloaded later"

echo "✅ EC2 instance setup complete!"
echo "🌐 Your application will be available at: https://brb.elvisquant.com"
echo "🔧 Use AWS Systems Manager Session Manager to access the instance"
echo "📊 Check GitHub Actions for deployment status"