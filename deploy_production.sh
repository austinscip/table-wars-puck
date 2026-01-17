#!/bin/bash
# TABLE WARS - Production Deployment Script
#
# This script automates the deployment process for Table Wars
# Run with: ./deploy_production.sh

set -e  # Exit on error

echo "🚀 TABLE WARS - Production Deployment"
echo "======================================"
echo ""

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Prerequisites OK"
echo ""

# Check .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp server/.env.example .env
    echo "📝 Please edit .env with your production values:"
    echo "   - SECRET_KEY (generate with: python3 -c 'import secrets; print(secrets.token_hex(32))')"
    echo "   - DB_PASSWORD"
    echo "   - DOMAIN"
    echo ""
    read -p "Press Enter after editing .env to continue..."
fi

# Validate .env
echo "🔍 Validating .env configuration..."

if grep -q "change_me_in_production" .env || grep -q "change_this_secret_key_in_production" .env; then
    echo "❌ ERROR: Default values detected in .env"
    echo "   Please update SECRET_KEY and DB_PASSWORD with secure values"
    exit 1
fi

echo "✅ .env validation OK"
echo ""

# Check SSL certificates
echo "🔒 Checking SSL certificates..."

if [ ! -f "nginx/ssl/cert.pem" ] || [ ! -f "nginx/ssl/key.pem" ]; then
    echo "⚠️  SSL certificates not found"
    echo ""
    echo "Choose SSL setup method:"
    echo "  1) Let's Encrypt (recommended for production)"
    echo "  2) Self-signed certificate (development only)"
    echo "  3) Skip (I'll add certificates manually)"
    read -p "Enter choice [1-3]: " ssl_choice

    case $ssl_choice in
        1)
            read -p "Enter your domain name: " domain
            echo "📜 Obtaining Let's Encrypt certificate for $domain..."
            sudo certbot certonly --standalone -d "$domain"
            mkdir -p nginx/ssl
            sudo cp "/etc/letsencrypt/live/$domain/fullchain.pem" nginx/ssl/cert.pem
            sudo cp "/etc/letsencrypt/live/$domain/privkey.pem" nginx/ssl/key.pem
            sudo chmod 600 nginx/ssl/*
            echo "✅ SSL certificates installed"
            ;;
        2)
            echo "🔐 Generating self-signed certificate..."
            mkdir -p nginx/ssl
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout nginx/ssl/key.pem \
                -out nginx/ssl/cert.pem \
                -subj "/CN=localhost"
            chmod 600 nginx/ssl/*
            echo "✅ Self-signed certificate created"
            echo "⚠️  WARNING: Self-signed certificates are not secure for production!"
            ;;
        3)
            echo "⏭️  Skipping SSL setup. Remember to add certificates before starting!"
            ;;
        *)
            echo "❌ Invalid choice"
            exit 1
            ;;
    esac
fi

echo ""

# Pull latest code
echo "📥 Pulling latest code..."
if [ -d ".git" ]; then
    git pull origin main || echo "⚠️  Could not pull latest code. Continuing with local version..."
fi

echo ""

# Build Docker images
echo "🏗️  Building Docker images..."
docker-compose build --no-cache

echo ""

# Stop existing containers
if docker-compose ps -q | grep -q .; then
    echo "🛑 Stopping existing containers..."
    docker-compose down
fi

echo ""

# Start services
echo "🚀 Starting services..."
docker-compose up -d

echo ""

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🏥 Health check..."
for i in {1..30}; do
    if docker-compose ps | grep -q "healthy"; then
        echo "✅ Services are healthy!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  Services did not become healthy in time. Check logs:"
        echo "   docker-compose logs -f"
        exit 1
    fi
    sleep 2
done

echo ""

# Display status
echo "📊 Service Status:"
docker-compose ps

echo ""
echo "🎉 Deployment complete!"
echo ""
echo "📍 Access Points:"
echo "   • Main App: https://$(grep DOMAIN .env | cut -d'=' -f2)"
echo "   • Admin: https://$(grep DOMAIN .env | cut -d'=' -f2)/admin"
echo "   • Analytics: https://$(grep DOMAIN .env | cut -d'=' -f2)/admin/analytics/<bar-slug>"
echo ""
echo "📝 Management Commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop: docker-compose down"
echo "   • Restart: docker-compose restart"
echo "   • Status: docker-compose ps"
echo ""
echo "🔧 Troubleshooting:"
echo "   • If WebSocket fails, check nginx logs: docker-compose logs nginx"
echo "   • If database fails, check postgres logs: docker-compose logs postgres"
echo "   • Full documentation: See DEPLOYMENT.md"
echo ""
