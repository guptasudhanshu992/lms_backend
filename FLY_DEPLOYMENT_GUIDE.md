# Fly.io Deployment Guide for LMS Backend

## Prerequisites

1. **Install Fly.io CLI**
   ```bash
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   
   # macOS/Linux
   curl -L https://fly.io/install.sh | sh
   ```

2. **Sign up and login**
   ```bash
   fly auth signup
   # or if you have an account
   fly auth login
   ```

## Initial Setup

### 1. Launch the App
```bash
cd E:\Sudhanshu\Website\fastapi\lms\backend

# Launch with auto-configuration (uses fly.toml)
fly launch --no-deploy

# Or manually specify region
fly launch --region sea --no-deploy
```

Available regions:
- `iad` - Washington DC, USA
- `lhr` - London, UK
- `sin` - Singapore
- `sea` - Seattle, USA
- `syd` - Sydney, Australia

### 2. Create Volume for Persistent Storage
```bash
# Create 1GB volume for database, uploads, logs
fly volumes create lms_data --region sea --size 1
```

### 3. Set Environment Secrets
```bash
# Required secrets
fly secrets set SECRET_KEY="your-super-secret-key-here-min-32-chars"
fly secrets set ADMIN_EMAIL="admin@yourdomain.com"
fly secrets set ADMIN_PASSWORD="Admin@123456"

# Database (optional if using volume-based SQLite)
# For PostgreSQL (recommended for production):
fly secrets set DATABASE_URL="postgresql://user:pass@host:5432/dbname"

# Email configuration (for password reset)
fly secrets set SMTP_HOST="smtp.gmail.com"
fly secrets set SMTP_PORT="587"
fly secrets set SMTP_USER="your-email@gmail.com"
fly secrets set SMTP_PASSWORD="your-app-specific-password"
fly secrets set FROM_EMAIL="noreply@yourdomain.com"

# Stripe (for payments)
fly secrets set STRIPE_SECRET_KEY="sk_live_..."
fly secrets set STRIPE_PUBLISHABLE_KEY="pk_live_..."
fly secrets set STRIPE_WEBHOOK_SECRET="whsec_..."

# Cloudflare (if using video upload features)
fly secrets set CLOUDFLARE_ACCOUNT_ID="your-account-id"
fly secrets set CLOUDFLARE_API_TOKEN="your-api-token"
fly secrets set CLOUDFLARE_R2_ACCESS_KEY_ID="your-access-key"
fly secrets set CLOUDFLARE_R2_SECRET_ACCESS_KEY="your-secret-key"
fly secrets set CLOUDFLARE_R2_BUCKET_NAME="your-bucket-name"

# CORS (update with your frontend domain)
fly secrets set ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
fly secrets set FRONTEND_URL="https://yourdomain.com"
```

### 4. Deploy
```bash
# Deploy the application
fly deploy

# Watch logs during deployment
fly logs
```

## Database Options

### Option 1: SQLite (Simple, Volume-based)
Default setup uses SQLite stored on persistent volume.

**Pros**: Simple, no extra cost  
**Cons**: Single machine only, limited scalability

```bash
# Database will be at /app/data/lms.db
# Automatically created on first run
```

### Option 2: Fly Postgres (Recommended for Production)
```bash
# Create a Postgres cluster
fly postgres create --name lms-db --region sea

# Attach to your app
fly postgres attach lms-db

# This automatically sets DATABASE_URL secret
```

### Option 3: External Database (Most Flexible)
Use Supabase, Neon, or any PostgreSQL provider:

```bash
# Just set the DATABASE_URL secret
fly secrets set DATABASE_URL="postgresql://user:pass@external-host:5432/dbname"
```

## Environment Configuration

Update your `.env` or set these via secrets:

```bash
# Production settings
fly secrets set ENVIRONMENT="production"
fly secrets set DEBUG="False"

# App configuration
fly secrets set APP_NAME="Your LMS Platform"
fly secrets set RATE_LIMIT_PER_MINUTE="60"

# JWT tokens
fly secrets set ALGORITHM="HS256"
fly secrets set ACCESS_TOKEN_EXPIRE_MINUTES="30"
fly secrets set REFRESH_TOKEN_EXPIRE_DAYS="7"
```

## Scaling

### Auto-scaling (Recommended)
The `fly.toml` is configured to auto-scale:
- Scales to 0 when idle (saves costs)
- Auto-starts on incoming requests
- Scales up based on load

```bash
# View current scaling
fly scale show

# Set min/max machines
fly scale count 1-3  # Run 1-3 machines based on load

# Adjust VM size if needed
fly scale vm shared-cpu-1x  # 1 CPU, 256MB RAM (cheapest)
fly scale vm shared-cpu-2x  # 2 CPUs, 512MB RAM
fly scale vm dedicated-cpu-1x  # Dedicated CPU
```

### Manual scaling
```bash
# Scale to specific number
fly scale count 2

# View current machines
fly status

# View machine details
fly machine list
```

## Monitoring

### View Logs
```bash
# Real-time logs
fly logs

# Historical logs
fly logs --history

# Filter by level
fly logs --level error
```

### Health Checks
```bash
# Check app health
fly status

# View health check details
fly checks list

# SSH into machine
fly ssh console
```

### Metrics
```bash
# View app metrics
fly dashboard

# Or open web dashboard
fly dashboard -o
```

## Custom Domain Setup

### 1. Add Certificate
```bash
# Add your domain
fly certs add yourdomain.com

# Add www subdomain
fly certs add www.yourdomain.com

# Check certificate status
fly certs show yourdomain.com
```

### 2. Configure DNS
Add these records to your DNS provider:

```
# For yourdomain.com
A     @     <your-fly-ip>
AAAA  @     <your-fly-ipv6>

# For www.yourdomain.com
CNAME www   yourdomain.com
```

Get your IPs:
```bash
fly ips list
```

### 3. Update CORS Settings
```bash
fly secrets set ALLOWED_ORIGINS="https://yourdomain.com,https://www.yourdomain.com"
fly secrets set FRONTEND_URL="https://yourdomain.com"
```

## Troubleshooting

### Check App Status
```bash
fly status
fly checks list
```

### View Recent Errors
```bash
fly logs --level error
```

### SSH into Container
```bash
fly ssh console

# Once inside:
cd /app
python -c "from app.main import app; print('App loaded successfully')"
ls -la
```

### Restart App
```bash
fly apps restart
```

### Check Environment Variables
```bash
fly ssh console -C "env | grep -E 'DATABASE|SECRET|ADMIN'"
```

### Database Issues
```bash
# Check if database exists
fly ssh console -C "ls -la /app/data/"

# Run migrations manually
fly ssh console
cd /app
alembic upgrade head
```

### Fix Health Check Failures
```bash
# Test health endpoint locally in container
fly ssh console -C "curl http://localhost:8000/health"

# Check if uvicorn is running
fly ssh console -C "ps aux | grep uvicorn"
```

## Cost Estimation

### Free Tier (Hobby Plan)
- **3 shared-cpu-1x machines** (256MB RAM each)
- **3GB persistent volumes**
- **160GB outbound data transfer/month**
- **Cost**: $0/month (includes $5 credit)

### Typical Production Setup
- **1 shared-cpu-1x machine** (always running): ~$2/month
- **1GB volume**: ~$0.15/month
- **Bandwidth**: First 100GB free, then $0.02/GB
- **Postgres (optional)**: Starting at $0/month (512MB) to $15/month (1GB)
- **Estimated Total**: $2-5/month (without database), $10-20/month (with Postgres)

## Updating Your App

### Deploy New Version
```bash
# Deploy changes
fly deploy

# Deploy specific Dockerfile
fly deploy --dockerfile Dockerfile

# Force rebuild
fly deploy --build-only
```

### Zero-Downtime Deployment
Fly.io handles this automatically with the configuration in `fly.toml`.

### Rollback
```bash
# List releases
fly releases

# Rollback to previous version
fly releases rollback <version-number>
```

## Backup & Recovery

### Database Backup (SQLite on Volume)
```bash
# SSH and backup
fly ssh console -C "sqlite3 /app/data/lms.db .dump" > backup.sql

# Restore
cat backup.sql | fly ssh console -C "sqlite3 /app/data/lms.db"
```

### Database Backup (Postgres)
```bash
# Automatic backups are enabled
fly postgres backup list

# Manual backup
fly postgres backup create

# Restore from backup
fly postgres restore <backup-id>
```

### Volume Snapshots
```bash
# Create snapshot
fly volumes snapshots create lms_data

# List snapshots
fly volumes snapshots list lms_data

# Restore from snapshot
fly volumes restore lms_data <snapshot-id>
```

## Production Checklist

- [ ] Set all required secrets
- [ ] Configure custom domain
- [ ] Set up database (Postgres recommended)
- [ ] Update CORS settings for production domain
- [ ] Test payment webhooks (Stripe)
- [ ] Configure email sending (SMTP)
- [ ] Set up monitoring/alerts
- [ ] Configure backups
- [ ] Test auto-scaling behavior
- [ ] Update frontend API URL to production backend
- [ ] Test all API endpoints
- [ ] Monitor logs for errors
- [ ] Set up uptime monitoring (e.g., UptimeRobot)

## Useful Commands

```bash
# Quick reference
fly status                  # App status
fly logs                    # View logs
fly ssh console            # SSH into app
fly dashboard              # Open web dashboard
fly scale show             # View scaling config
fly secrets list           # List secrets (values hidden)
fly releases               # View deployment history
fly apps restart           # Restart app
fly apps destroy           # Delete app (careful!)
```

## Support & Documentation

- **Fly.io Docs**: https://fly.io/docs/
- **Status Page**: https://status.flyio.net/
- **Community**: https://community.fly.io/
- **Pricing**: https://fly.io/docs/about/pricing/

## Next Steps

1. **Deploy Frontend**: Consider deploying React frontend to:
   - Vercel (recommended)
   - Cloudflare Pages
   - Fly.io (same platform)

2. **Set up CI/CD**: Automate deployments with GitHub Actions:
   ```yaml
   # .github/workflows/deploy.yml
   name: Deploy to Fly.io
   on:
     push:
       branches: [main]
   jobs:
     deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         - uses: superfly/flyctl-actions/setup-flyctl@master
         - run: flyctl deploy --remote-only
           env:
             FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
   ```

3. **Monitoring**: Set up external monitoring (UptimeRobot, Pingdom)

4. **CDN**: Use Cloudflare for:
   - Static assets caching
   - DDoS protection
   - SSL/TLS
   - Load balancing

Your FastAPI backend is now production-ready on Fly.io! 🚀
