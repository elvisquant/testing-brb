#!/bin/bash
set -e

# Update system
echo "🔄 Updating system packages..."
sudo yum update -y

# --- THE FIX IS HERE ---
# Install Docker using the correct command for Amazon Linux 2023
echo "🐳 Installing Docker..."
sudo yum install -y docker
# --- END OF FIX ---

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
echo "📦 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
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

# Download the Docker Compose file
echo "📄 Downloading Docker Compose file..."
# IMPORTANT: Replace YOUR_USERNAME/YOUR_REPO with your actual GitHub username and repository
sudo curl -o docker-compose.prod.yml https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPO/main/docker-compose.prod.yml
sudo chown ec2-user:ec2-user docker-compose.prod.yml

# Wait for 60 seconds to allow the DNS record to propagate globally.
echo "⏳ Waiting 60 seconds for DNS propagation before starting services..."
sleep 60

# Now, pull the image and start the services as the ec2-user
echo "🐳 Pulling initial Docker image and starting services..."
sudo -u ec2-user /usr/local/bin/docker-compose -f docker-compose.prod.yml pull
sudo -u ec2-user /usr/local/bin/docker-compose -f docker-compose.prod.yml up -d

echo "✅ EC2 instance setup complete!"
echo "🌐 Your application will be available at: https://brb.elvisquant.com"
echo "🔧 Use AWS Systems Manager Session Manager to access the instance"