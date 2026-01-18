# TABLE WARS - Production Deployment Guide

## 🎯 Current Status
✅ Docker deployment working locally on http://localhost and https://localhost
✅ PostgreSQL database initialized with all tables
✅ WebSocket support configured
✅ All game modes functional

## 🚀 Deployment Options

### Option 1: Cloud VPS Deployment (Recommended for Production)
**Best for:** Public-facing deployment, multiple locations, remote management

**Providers:**
- **DigitalOcean** ($6-12/month) - Simple, developer-friendly
- **Linode/Akamai** ($5-10/month) - Reliable, good docs
- **AWS Lightsail** ($5-10/month) - Amazon ecosystem integration
- **Vultr** ($6/month) - Good performance
- **Hetzner** ($4-8/month) - Best value, Europe-based

**Steps:**
1. Provision Ubuntu 22.04+ server with 2GB+ RAM
2. Point domain DNS to server IP
3. SSH into server and clone repository
4. Run deployment script
5. Configure Let's Encrypt SSL
6. Set up automatic backups

**Pros:** Accessible from anywhere, scalable, professional SSL, easy backups
**Cons:** Monthly cost, requires domain name, internet-dependent

---

### Option 2: Local Network Deployment
**Best for:** Single bar/restaurant location, offline operation

**Hardware Options:**
- **Raspberry Pi 4 (4GB+)** ($50-80) - Low power, compact
- **Intel NUC / Mini PC** ($200-400) - More powerful
- **Repurpose old laptop/desktop** (Free) - Good for testing

**Steps:**
1. Install Ubuntu Server on hardware
2. Configure static IP on local network (e.g., 192.168.1.100)
3. Clone repository and deploy
4. Set up router port forwarding (optional, for remote access)
5. Configure automatic database backups to USB drive

**Pros:** No monthly cost, works offline, full control, low latency
**Cons:** Physical hardware management, limited remote access, no automatic SSL

---

### Option 3: Platform-as-a-Service (PaaS)
**Best for:** Quick deployment, minimal devops

**Providers:**
- **Railway.app** ($5-20/month) - Modern, easy to use
- **Render.com** ($7-25/month) - Great free tier, PostgreSQL included
- **Fly.io** ($0-15/month) - Global deployment, WebSocket support
- **Heroku** ($7-25/month) - Established platform

**Steps:**
1. Connect GitHub repository to platform
2. Configure environment variables
3. Add PostgreSQL addon
4. Deploy with one click
5. Point domain to provided URL

**Pros:** Easiest deployment, automatic SSL, managed database, auto-scaling
**Cons:** Higher cost, vendor lock-in, less control

---

### Option 4: Hybrid Approach (Local + Cloud)
**Best for:** Multiple bar locations with central management

**Architecture:**
- **Local servers** at each bar (Raspberry Pi/NUC) for low-latency gameplay
- **Cloud database** (managed PostgreSQL) for centralized analytics
- **Cloud dashboard** for remote monitoring across all locations

**Pros:** Best of both worlds, offline gameplay, centralized data
**Cons:** More complex setup, requires VPN or secure tunnels

---

## 📝 Domain Name Selection

### Domain Registrars (Recommended)
- **Namecheap** - Good pricing, free WHOIS privacy
- **Porkbun** - Cheapest, excellent customer service
- **Cloudflare** - At-cost pricing, great DNS management
- **Google Domains** → **Squarespace Domains** - Simple interface

### Domain Ideas
- `tablewars.io` - Modern, tech feel
- `pucktrivia.com` - Descriptive
- `[yourbarname]games.com` - Branded
- `smartpuck.io` - Product-focused

### Cost: $10-15/year for .com, $5-8/year for .io/.app

---

## 🔒 SSL Certificate Options

### Option A: Let's Encrypt (Free, Automated)
**Best for:** Cloud deployments with domain name
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is configured automatically
```

### Option B: Cloudflare SSL (Free, Managed)
**Best for:** Easy setup with Cloudflare DNS
- Point domain to Cloudflare nameservers
- Enable "Full (Strict)" SSL mode
- Certificate managed automatically

### Option C: Self-Signed (Current Setup)
**Best for:** Local network deployments only
- Already configured
- Browser warnings for external users
- Free, no domain required

---

## 💾 Database Backup Strategies

### Automated Backups (Recommended)

#### 1. Local Backup Script
Create `/Users/austinscipione/table-wars-puck/scripts/backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/app/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker exec tablewars-db pg_dump -U tablewars_user tablewars_prod > $BACKUP_DIR/backup_$TIMESTAMP.sql
# Keep last 7 days
find $BACKUP_DIR -name "backup_*.sql" -mtime +7 -delete
```

Add to crontab:
```bash
0 2 * * * /path/to/backup.sh  # Daily at 2 AM
```

#### 2. Cloud Backup (AWS S3)
```bash
#!/bin/bash
# After local backup, sync to S3
aws s3 sync /app/backups s3://tablewars-backups/$(date +%Y-%m)/ --delete
```

#### 3. Managed PostgreSQL Backups
If using cloud providers (DigitalOcean, AWS RDS, etc.), enable:
- Daily automated snapshots
- Point-in-time recovery
- Cross-region replication (optional)

### Backup Testing
```bash
# Test restore monthly
docker exec -i tablewars-db psql -U tablewars_user tablewars_test < backup_file.sql
```

---

## 📊 Monitoring & Logging (Optional)

### Basic Monitoring (Free)
```bash
# View logs
docker-compose logs -f app
docker-compose logs -f postgres

# Monitor resources
docker stats

# Check disk space
df -h
```

### Advanced Monitoring

#### 1. Uptime Monitoring
- **UptimeRobot** (Free tier) - Checks if site is up every 5 minutes
- **Healthchecks.io** (Free tier) - Monitors scheduled tasks

#### 2. Application Monitoring
- **Sentry** (Free tier) - Error tracking
- **Better Stack** (Free tier) - Logs + uptime

#### 3. Server Monitoring
- **Netdata** (Free) - Real-time performance monitoring
- **Prometheus + Grafana** - Advanced metrics

---

## 🎬 Quick Start: Recommended Path

### For Single Bar Location (Offline-First)
1. **Hardware:** Raspberry Pi 4 (4GB) - $80
2. **Domain:** Not required (use local IP: `http://192.168.1.100`)
3. **SSL:** Self-signed (current setup) or skip for local network
4. **Backup:** USB drive + weekly manual backups
5. **Total cost:** $80 one-time

### For Cloud Deployment (Internet-Required)
1. **Server:** DigitalOcean Droplet (2GB RAM) - $12/month
2. **Domain:** Porkbun .io domain - $8/year
3. **SSL:** Let's Encrypt (free, auto-renew)
4. **Backup:** DigitalOcean snapshots ($1-2/month)
5. **Total cost:** ~$14/month

### For Easy Deployment (No DevOps)
1. **Platform:** Render.com
2. **Domain:** Namecheap .com - $12/year
3. **SSL:** Included automatically
4. **Backup:** Included in platform
5. **Total cost:** ~$8/month + $12/year domain

---

## 📋 Pre-Deployment Checklist

Before deploying to production:

- [ ] Choose deployment method (cloud/local/PaaS)
- [ ] Register domain name (if cloud deployment)
- [ ] Update `.env` file with production values
- [ ] Configure DNS records
- [ ] Set up SSL certificate
- [ ] Test database backups
- [ ] Configure firewall rules
- [ ] Set up monitoring (optional)
- [ ] Test WebSocket connections
- [ ] Load test with multiple pucks
- [ ] Create admin documentation
- [ ] Set up automated backups

---

## 🆘 Need Help?

For specific deployment assistance:
1. Choose your preferred deployment option above
2. I'll provide detailed step-by-step instructions
3. We can configure everything together

Current deployment is ready for testing locally at https://localhost
