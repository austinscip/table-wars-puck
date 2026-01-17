# Table Wars - Production Deployment Guide

Complete guide for deploying Table Wars to production with Docker, PostgreSQL, and SSL.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (Docker)](#quick-start-docker)
3. [Environment Configuration](#environment-configuration)
4. [SSL/HTTPS Setup](#sslhttps-setup)
5. [Database Migration](#database-migration)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Hardware Requirements
- **Server**: 2 CPU cores, 4GB RAM minimum
- **Storage**: 20GB available disk space
- **Network**: Static IP or domain name recommended

### Software Requirements
- Docker 24.0+ and Docker Compose 2.0+
- OR Python 3.11+ for non-Docker deployment
- PostgreSQL 16+ (included in Docker setup)
- Nginx (included in Docker setup)

---

## Quick Start (Docker)

### 1. Clone Repository
```bash
git clone https://github.com/your-org/table-wars-puck.git
cd table-wars-puck
```

### 2. Configure Environment
```bash
# Create production environment file
cp server/.env.example .env

# Edit with your production values
nano .env
```

**Required changes in `.env`:**
```bash
# Generate secure secret key
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

# Set strong database password
DB_PASSWORD=your_secure_database_password_here

# Set your domain
DOMAIN=yourdomain.com
```

### 3. SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt-get install certbot

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com

# Copy to nginx directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
sudo chmod 600 nginx/ssl/*
```

#### Option B: Self-Signed (Development Only)
```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/CN=localhost"
```

### 4. Start Services
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 5. Initialize Database
```bash
# Database tables are auto-created on first run
# Verify with:
docker-compose exec postgres psql -U tablewars_user -d tablewars_prod -c "\dt"
```

### 6. Access Application
- **HTTPS**: https://yourdomain.com
- **Admin**: https://yourdomain.com/admin
- **Analytics**: https://yourdomain.com/admin/analytics/your-bar-slug
- **API**: https://yourdomain.com/api/stats

---

## Environment Configuration

### Complete .env Reference

```bash
# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================
DATABASE_URL=postgresql://tablewars_user:DB_PASSWORD@postgres:5432/tablewars_prod
DB_PASSWORD=change_me_in_production

# =============================================================================
# FLASK CONFIGURATION
# =============================================================================
SECRET_KEY=change_this_secret_key_in_production
DEBUG=False
HOST=0.0.0.0
PORT=5001
FLASK_ENV=production

# =============================================================================
# DOMAIN & SSL
# =============================================================================
DOMAIN=yourdomain.com

# =============================================================================
# OPTIONAL: MONITORING & LOGGING
# =============================================================================
# Sentry DSN for error tracking
# SENTRY_DSN=https://xxx@sentry.io/xxx

# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# =============================================================================
# OPTIONAL: FIRMWARE OTA
# =============================================================================
# Base URL for firmware downloads
FIRMWARE_BASE_URL=https://yourdomain.com/firmware
```

---

## SSL/HTTPS Setup

### Production SSL (Let's Encrypt)

#### Initial Setup
```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot

# Obtain certificate (domain must point to server)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem nginx/ssl/key.pem
sudo chmod 600 nginx/ssl/*

# Restart nginx
docker-compose restart nginx
```

#### Auto-Renewal (Cron Job)
```bash
# Add to crontab (crontab -e)
0 3 * * * certbot renew --quiet && \
  cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /path/to/table-wars-puck/nginx/ssl/cert.pem && \
  cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /path/to/table-wars-puck/nginx/ssl/key.pem && \
  docker-compose -f /path/to/table-wars-puck/docker-compose.yml restart nginx
```

---

## Database Migration

### SQLite to PostgreSQL Migration

If migrating from local SQLite to production PostgreSQL:

```bash
# 1. Export SQLite data
sqlite3 tablewars.db .dump > backup.sql

# 2. Convert SQLite syntax to PostgreSQL
# Remove SQLite-specific commands
sed -i '/BEGIN TRANSACTION;/d' backup.sql
sed -i '/COMMIT;/d' backup.sql
sed -i 's/AUTOINCREMENT/SERIAL/g' backup.sql

# 3. Import to PostgreSQL
docker-compose exec -T postgres psql -U tablewars_user -d tablewars_prod < backup.sql
```

### Backup & Restore

#### Backup
```bash
# Automated daily backup script
docker-compose exec postgres pg_dump -U tablewars_user tablewars_prod \
  | gzip > backups/tablewars_$(date +%Y%m%d).sql.gz
```

#### Restore
```bash
gunzip -c backups/tablewars_20240117.sql.gz | \
  docker-compose exec -T postgres psql -U tablewars_user -d tablewars_prod
```

---

## Monitoring

### Health Checks

```bash
# Application health
curl https://yourdomain.com/api/stats

# Container health
docker-compose ps
docker-compose exec app python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/api/stats').read()"

# Database health
docker-compose exec postgres pg_isready -U tablewars_user -d tablewars_prod
```

### Logs

```bash
# View all logs
docker-compose logs -f

# Application logs only
docker-compose logs -f app

# Nginx access logs
docker-compose logs -f nginx

# Database logs
docker-compose logs -f postgres

# Last 100 lines
docker-compose logs --tail=100 app
```

### Resource Usage

```bash
# Container stats
docker stats

# Disk usage
docker system df

# Clean up unused images/containers
docker system prune -a
```

---

## Troubleshooting

### Common Issues

#### 1. WebSocket Connection Fails
**Symptom**: Real-time updates don't work

**Solution**:
```bash
# Check nginx WebSocket proxy configuration
docker-compose exec nginx nginx -t
docker-compose restart nginx

# Verify Socket.IO endpoint
curl -I https://yourdomain.com/socket.io/
```

#### 2. Database Connection Refused
**Symptom**: `could not connect to server`

**Solution**:
```bash
# Check database is running
docker-compose ps postgres

# Check connection string in .env
cat .env | grep DATABASE_URL

# Restart database
docker-compose restart postgres
```

#### 3. SSL Certificate Errors
**Symptom**: `NET::ERR_CERT_AUTHORITY_INVALID`

**Solution**:
```bash
# Verify certificate files exist
ls -la nginx/ssl/

# Check certificate expiration
openssl x509 -in nginx/ssl/cert.pem -noout -dates

# Renew Let's Encrypt certificate
sudo certbot renew --force-renewal
```

#### 4. High Memory Usage
**Symptom**: Server becomes slow/unresponsive

**Solution**:
```bash
# Check memory usage
docker stats

# Reduce worker count in Dockerfile (gunicorn --workers 1)
# Or increase server RAM

# Restart containers
docker-compose restart
```

### Getting Help

- **GitHub Issues**: https://github.com/your-org/table-wars-puck/issues
- **Documentation**: See README.md
- **Logs**: Always include `docker-compose logs` output when reporting issues

---

## Production Checklist

Before going live:

- [ ] Generate secure SECRET_KEY
- [ ] Set strong DB_PASSWORD
- [ ] Configure SSL with valid certificate
- [ ] Set DEBUG=False in .env
- [ ] Point domain DNS to server IP
- [ ] Set up automated backups
- [ ] Configure SSL auto-renewal
- [ ] Test WebSocket connections
- [ ] Test firmware OTA updates
- [ ] Set up monitoring/alerting
- [ ] Review nginx access logs
- [ ] Test disaster recovery procedure

---

## Maintenance

### Updates

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs -f app
```

### Scaling

To handle more traffic:

1. **Horizontal Scaling**: Run multiple app containers
```yaml
# docker-compose.yml
services:
  app:
    deploy:
      replicas: 3
```

2. **Vertical Scaling**: Increase container resources
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

---

## Security Best Practices

1. **Change default credentials** in .env
2. **Restrict database access** to app container only
3. **Use firewall** to block unnecessary ports
4. **Enable fail2ban** for brute-force protection
5. **Regular security updates**: `apt update && apt upgrade`
6. **Monitor logs** for suspicious activity
7. **Backup encryption**: Encrypt database backups
8. **API rate limiting**: Add rate limits to nginx

---

## License

See LICENSE file
