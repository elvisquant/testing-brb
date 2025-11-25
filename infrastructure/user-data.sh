#!/bin/bash
set -e

# --- UBUNTU SETUP ---
export DEBIAN_FRONTEND=noninteractive
# Update system package lists ONLY.
echo "🔄 Updating system package lists..."
sudo apt-get update -y

# Install Docker using apt
echo "🐳 Installing Docker..."
sudo apt-get install -y docker.io

# Standard Docker setup
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -a -G docker ubuntu
# --- END OF UBUNTU SETUP ---

# Install Docker Compose
echo "📦 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# The rest of the setup (creating files, starting services) will now be handled
# by the much more reliable SSH deployment step. This ensures the instance
# boots as quickly as possible.

echo "✅ EC2 instance core setup complete! Docker is installed and running."