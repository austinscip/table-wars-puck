# TABLE WARS - Quick Start Guide

## 🎮 What You Have Now

Your TABLE WARS system is **fully deployed** and running locally:

- ✅ Docker containers running (app, database, nginx)
- ✅ Database initialized with all tables
- ✅ WebSocket support working
- ✅ All 10+ game modes functional
- ✅ Backup system configured

## 🌐 Access Points

**Local Development:**
- Main site: https://localhost
- Game gallery: https://localhost/games
- Puck simulator: https://localhost/test/puck-simulator
- API stats: https://localhost/api/stats

## 🎯 Common Commands

### Start/Stop/Restart
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose stop

# Restart a specific service
docker-compose restart app

# View logs
docker-compose logs -f app

# Check container status
docker-compose ps
```

### Database Backups
```bash
# Create backup (automated script)
./scripts/backup_database.sh

# Restore from backup
./scripts/restore_database.sh /path/to/backup.sql.gz

# Manual backup
docker exec tablewars-db pg_dump -U tablewars_user tablewars_prod > backup.sql
```

### Database Access
```bash
# Connect to PostgreSQL
docker exec -it tablewars-db psql -U tablewars_user -d tablewars_prod

# View tables
docker exec tablewars-db psql -U tablewars_user -d tablewars_prod -c "\dt"

# Count games played
docker exec tablewars-db psql -U tablewars_user -d tablewars_prod -c "SELECT COUNT(*) FROM games;"
```

### Troubleshooting
```bash
# Rebuild containers after code changes
docker-compose down
docker-compose build
docker-compose up -d

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d

# Check container health
docker-compose ps
docker inspect tablewars-app | grep -A10 Health
```

## 📦 What's Next?

You have 3 main paths forward:

### Option 1: Keep Testing Locally
**Current state is perfect for:**
- Testing all game modes
- Developing new features
- Prototyping with pucks
- Demo to investors/partners

**No additional setup needed!**

### Option 2: Deploy to Cloud (Internet Access)
**Choose this if you need:**
- Access from anywhere
- Multiple locations
- Professional domain (tablewars.com)
- Scalability

**Next steps:**
1. Register domain name (~$10-15/year)
2. Choose cloud provider (DigitalOcean, AWS, etc.)
3. Deploy Docker setup to server
4. Configure Let's Encrypt SSL
5. Point domain DNS to server

**See:** DEPLOYMENT_GUIDE.md for detailed instructions

### Option 3: Deploy Locally at Bar
**Choose this if you need:**
- Single location deployment
- Offline operation
- No monthly costs
- Physical hardware control

**Next steps:**
1. Get Raspberry Pi 4 (4GB+) or dedicated PC
2. Install Ubuntu Server
3. Clone repository to device
4. Run Docker deployment
5. Configure static IP on network

**See:** DEPLOYMENT_GUIDE.md for detailed instructions

## 🆘 Getting Help

**Logs to check:**
1. Application: docker-compose logs app
2. Database: docker-compose logs postgres
3. Nginx: docker-compose logs nginx
4. Docker: docker ps -a

**Common issues:**
- Port conflicts: Change ports in docker-compose.yml
- Database errors: Check PostgreSQL logs
- WebSocket issues: Verify nginx proxy settings
- SSL warnings: Normal for self-signed certificates

## 🎉 You're All Set!

Your TABLE WARS deployment is production-ready locally. When you're ready to deploy to production, refer to DEPLOYMENT_GUIDE.md for your chosen deployment method.

**Current test URL:** https://localhost/games

Enjoy building the future of interactive bar gaming! 🍻🎮
