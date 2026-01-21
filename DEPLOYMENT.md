# LIMS.Pro Production Deployment Guide

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Backend Deployment](#backend-deployment)
3. [Frontend Deployment](#frontend-deployment)
4. [Database Setup](#database-setup)
5. [Security Configuration](#security-configuration)
6. [Monitoring & Logging](#monitoring--logging)
7. [Backup Strategy](#backup-strategy)
8. [Go-Live Checklist](#go-live-checklist)

---

## Prerequisites

### System Requirements
- Docker 20.10+ and Docker Compose 2.0+
- Node.js 18+ (for frontend build)
- MongoDB 6.0+ (managed service recommended)
- SSL/TLS certificates
- Domain name with DNS configured

### Required Environment Variables
```bash
# Backend (REQUIRED)
ENVIRONMENT=production
MONGO_URL=mongodb+srv://<user>:<pass>@<cluster>/<db>?retryWrites=true&w=majority
DB_NAME=lims_production
JWT_SECRET=<64-character-random-string>
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Optional Integrations
SENDGRID_API_KEY=SG.xxxxx
SENDGRID_FROM_EMAIL=noreply@yourdomain.com

# Frontend
REACT_APP_BACKEND_URL=https://api.yourdomain.com
```

---

## Backend Deployment

### Option 1: Docker Deployment (Recommended)

#### Dockerfile
```dockerfile
# Production Dockerfile for LIMS.Pro Backend
FROM python:3.11-slim

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create app user (non-root)
RUN useradd --create-home --shell /bin/bash app
WORKDIR /home/app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=app:app . .

# Create reports directory
RUN mkdir -p reports && chown app:app reports

# Switch to non-root user
USER app

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/api/ || exit 1

# Run with gunicorn for production
CMD ["gunicorn", "server:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8001", "--access-logfile", "-", "--error-logfile", "-"]
```

#### Docker Compose
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    container_name: lims-backend
    restart: unless-stopped
    ports:
      - "8001:8001"
    environment:
      - ENVIRONMENT=production
      - MONGO_URL=${MONGO_URL}
      - DB_NAME=${DB_NAME}
      - JWT_SECRET=${JWT_SECRET}
      - CORS_ORIGINS=${CORS_ORIGINS}
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - SENDGRID_FROM_EMAIL=${SENDGRID_FROM_EMAIL}
    volumes:
      - ./reports:/home/app/reports
      - ./logs:/home/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/api/"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  nginx:
    image: nginx:alpine
    container_name: lims-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./frontend/build:/usr/share/nginx/html:ro
    depends_on:
      - backend

volumes:
  reports:
  logs:
```

#### Build and Deploy
```bash
# Build backend image
docker build -t lims-backend:latest -f Dockerfile.prod ./backend

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Option 2: Cloud Platform Deployment

#### AWS ECS / Fargate
```bash
# Push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin <account>.dkr.ecr.<region>.amazonaws.com
docker tag lims-backend:latest <account>.dkr.ecr.<region>.amazonaws.com/lims-backend:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/lims-backend:latest
```

#### Google Cloud Run
```bash
# Deploy to Cloud Run
gcloud run deploy lims-backend \
  --image gcr.io/<project>/lims-backend:latest \
  --platform managed \
  --region <region> \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,DB_NAME=lims_production"
```

---

## Frontend Deployment

### Build for Production
```bash
cd frontend

# Install dependencies
yarn install --frozen-lockfile

# Set environment
echo "REACT_APP_BACKEND_URL=https://api.yourdomain.com" > .env.production

# Build
yarn build

# Output in ./build directory
```

### Nginx Configuration
```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    # Redirect HTTP to HTTPS
    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    # HTTPS Server
    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
        ssl_prefer_server_ciphers off;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://api.yourdomain.com;" always;

        # Frontend (React SPA)
        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
            
            # Cache static assets
            location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
                expires 1y;
                add_header Cache-Control "public, immutable";
            }
        }

        # API Proxy
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            
            proxy_pass http://backend:8001;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Timeouts
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # Health check endpoint
        location /health {
            access_log off;
            return 200 "healthy";
            add_header Content-Type text/plain;
        }
    }
}
```

### CDN Setup (Optional)
```bash
# CloudFlare or AWS CloudFront recommended for:
# - Global CDN distribution
# - DDoS protection
# - Additional SSL/TLS layer
# - Caching optimization
```

---

## Database Setup

### MongoDB Atlas (Recommended)
1. Create M10+ cluster for production
2. Enable authentication
3. Configure IP whitelist
4. Enable encryption at rest
5. Set up VPC peering (optional)

### Connection String
```bash
# Format
mongodb+srv://<username>:<password>@<cluster>.mongodb.net/<database>?retryWrites=true&w=majority

# Example
MONGO_URL=mongodb+srv://lims_prod:SecurePassword123@cluster0.abc123.mongodb.net/lims_production?retryWrites=true&w=majority
```

### Indexes (Run once)
```javascript
// MongoDB Shell - Create indexes for performance
use lims_production;

// Users
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "role": 1 });

// Patients
db.patients.createIndex({ "patient_id": 1 }, { unique: true });
db.patients.createIndex({ "phone": 1 });
db.patients.createIndex({ "name": "text" });

// Orders
db.orders.createIndex({ "order_id": 1 }, { unique: true });
db.orders.createIndex({ "patient_id": 1 });
db.orders.createIndex({ "status": 1 });
db.orders.createIndex({ "created_at": -1 });

// Samples
db.samples.createIndex({ "sample_id": 1 }, { unique: true });
db.samples.createIndex({ "order_id": 1 });
db.samples.createIndex({ "barcode": 1 });

// Invoices
db.invoices.createIndex({ "invoice_id": 1 }, { unique: true });
db.invoices.createIndex({ "order_id": 1 });
db.invoices.createIndex({ "payment_status": 1 });

// Audit logs
db.audit_logs.createIndex({ "timestamp": -1 });
db.audit_logs.createIndex({ "user_id": 1 });
db.audit_logs.createIndex({ "entity_type": 1, "entity_id": 1 });

// TTL index for sessions (auto-expire after 7 days)
db.portal_sessions.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });
```

---

## Security Configuration

### Environment Variables Security
```bash
# Generate secure JWT secret
openssl rand -base64 64

# Use secrets manager in production
# AWS: AWS Secrets Manager
# GCP: Secret Manager
# Azure: Key Vault
```

### CORS Configuration
```python
# Production CORS - backend/.env
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://admin.yourdomain.com
```

### Disable Seed Endpoint in Production
```python
# In server.py - seed endpoint should check environment
@api_router.post("/seed", response_model=dict)
async def seed_data():
    if os.environ.get("ENVIRONMENT") == "production":
        raise HTTPException(status_code=403, detail="Seed endpoint disabled in production")
    # ... rest of seed logic
```

---

## Monitoring & Logging

### Application Logging
```python
# logging_config.py
import logging
import sys

def setup_logging(environment: str):
    log_level = logging.WARNING if environment == "production" else logging.DEBUG
    
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('/var/log/lims/app.log') if environment == "production" else logging.NullHandler()
        ]
    )
```

### Health Check Endpoint
```bash
# Already implemented at /api/
curl -f https://api.yourdomain.com/api/

# Expected response
{"message":"Laboratory Information System API","version":"1.0.0"}
```

### Monitoring Tools
```yaml
# docker-compose.monitoring.yml (optional)
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=secure_password
```

---

## Backup Strategy

### MongoDB Backup
```bash
#!/bin/bash
# backup.sh - Run daily via cron

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/mongodb"
MONGO_URI="$MONGO_URL"

# Create backup
mongodump --uri="$MONGO_URI" --out="$BACKUP_DIR/$DATE"

# Compress
tar -czf "$BACKUP_DIR/lims_backup_$DATE.tar.gz" "$BACKUP_DIR/$DATE"
rm -rf "$BACKUP_DIR/$DATE"

# Upload to S3 (optional)
aws s3 cp "$BACKUP_DIR/lims_backup_$DATE.tar.gz" s3://your-backup-bucket/mongodb/

# Retain last 30 days locally
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: lims_backup_$DATE.tar.gz"
```

### Cron Schedule
```bash
# /etc/cron.d/lims-backup
0 2 * * * root /opt/lims/backup.sh >> /var/log/lims-backup.log 2>&1
```

### Reports Backup
```bash
# Backup generated PDF reports
rsync -avz /app/backend/reports/ /backups/reports/
# Or sync to S3
aws s3 sync /app/backend/reports/ s3://your-backup-bucket/reports/
```

---

## Go-Live Checklist

### Pre-Deployment
- [ ] **Security Review**
  - [ ] JWT_SECRET is 64+ characters, randomly generated
  - [ ] CORS_ORIGINS restricted to production domains
  - [ ] DEBUG=false in environment
  - [ ] ENVIRONMENT=production set
  - [ ] Seed endpoint disabled/protected
  - [ ] All default passwords changed

- [ ] **Database**
  - [ ] Production MongoDB cluster created
  - [ ] Authentication enabled
  - [ ] IP whitelist configured
  - [ ] Indexes created
  - [ ] Backup schedule configured
  - [ ] Connection tested

- [ ] **Infrastructure**
  - [ ] SSL certificates installed
  - [ ] Domain DNS configured
  - [ ] Load balancer configured (if applicable)
  - [ ] Auto-scaling configured (if applicable)

### Deployment
- [ ] **Backend**
  - [ ] Docker image built and tested
  - [ ] Environment variables configured
  - [ ] Health check passing
  - [ ] Logs accessible

- [ ] **Frontend**
  - [ ] Production build created
  - [ ] REACT_APP_BACKEND_URL correct
  - [ ] Static assets served with caching
  - [ ] HTTPS redirect working

- [ ] **Integration**
  - [ ] API endpoints accessible
  - [ ] Authentication working
  - [ ] Database connected
  - [ ] PDF generation working

### Post-Deployment
- [ ] **Verification**
  - [ ] Login with test admin account
  - [ ] Create test patient
  - [ ] Create test order
  - [ ] Complete full workflow
  - [ ] Verify PDF generation
  - [ ] Check audit logs

- [ ] **Monitoring**
  - [ ] Health checks configured
  - [ ] Alerts set up
  - [ ] Log aggregation working
  - [ ] Backup verification

- [ ] **Documentation**
  - [ ] Admin credentials documented securely
  - [ ] Runbook created
  - [ ] Contact escalation defined

### First Admin Setup
```bash
# Create first admin user via API (one-time)
curl -X POST https://api.yourdomain.com/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourdomain.com",
    "password": "SecurePassword123!",
    "name": "System Administrator",
    "role": "admin",
    "phone": "+1234567890"
  }'
```

---

## Rollback Procedure

### Quick Rollback
```bash
# Rollback to previous Docker image
docker-compose -f docker-compose.prod.yml down
docker tag lims-backend:latest lims-backend:failed
docker tag lims-backend:previous lims-backend:latest
docker-compose -f docker-compose.prod.yml up -d
```

### Database Rollback
```bash
# Restore from backup
mongorestore --uri="$MONGO_URL" --drop /backups/mongodb/YYYYMMDD_HHMMSS/
```

---

## Support & Maintenance

### Log Locations
- Application: `/var/log/lims/app.log`
- Nginx: `/var/log/nginx/access.log`, `/var/log/nginx/error.log`
- Docker: `docker logs lims-backend`

### Common Issues
1. **502 Bad Gateway**: Backend container not running
2. **Connection refused**: Check MONGO_URL and network
3. **CORS errors**: Verify CORS_ORIGINS includes frontend domain
4. **JWT errors**: Check JWT_SECRET matches across deployments

---

**Document Version**: 1.0  
**Last Updated**: January 2026
