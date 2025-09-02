# 🚀 MCG Agent Setup Guide

Complete setup and deployment guide for the Multi-Corpus Governance Agent with FastAPI integration.

---

## 📋 Prerequisites

### System Requirements
- **Python**: 3.11 or higher
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 2GB free space
- **Network**: Internet access for package installation

### Required Services
- **Database**: SQLite (development) or PostgreSQL (production)
- **Redis**: For session management and caching
- **Git**: For version control

---

## ⚡ Quick Start

### 1. Automated Setup (Recommended)

```bash
# Clone repository
git clone https://github.com/dansasser/multi-corpus-governance-agent.git
cd multi-corpus-governance-agent

# Run automated setup
./scripts/setup.sh

# Initialize database
./scripts/init-db.sh --seed

# Start development server  
./scripts/start-dev.sh
```

**That's it!** The API will be available at `http://localhost:8000` with interactive documentation at `http://localhost:8000/docs`.

---

## 🔧 Manual Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/dansasser/multi-corpus-governance-agent.git
cd multi-corpus-governance-agent
```

### Step 2: Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install with development dependencies
pip install -e .[dev]

# Or install production only
pip install -e .

# Or install from requirements.txt
pip install -r requirements.txt
```

### Step 4: Environment Configuration

Create a `.env` file in the project root:

```bash
# Copy example environment file
cp .env.example .env

# Edit with your settings
nano .env
```

**Required Environment Variables:**

```bash
# Database Configuration
DATABASE_URL=sqlite:///./mcg_agent.db
# For PostgreSQL: postgresql://user:password@localhost:5432/mcg_agent

# Redis Configuration (session management)
REDIS_URL=redis://localhost:6379/0

# Security Keys (GENERATE SECURE VALUES!)
JWT_SECRET_KEY=your-super-secret-jwt-key-at-least-32-characters
ENCRYPTION_KEY=your-32-byte-encryption-key-for-data-protection

# API Keys
OPENAI_API_KEY=sk-your-openai-api-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# Server Configuration  
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Session Configuration
SESSION_EXPIRE_MINUTES=1440  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS=7

# Optional: External Services
# TWILIO_ACCOUNT_SID=your-twilio-sid
# TWILIO_AUTH_TOKEN=your-twilio-token
```

### Step 5: Database Setup

```bash
# Initialize database with tables and migrations
./scripts/init-db.sh

# Or with seed data
./scripts/init-db.sh --seed
```

---

## 🐳 Docker Setup (Alternative)

### Using Docker Compose

```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker Build

```bash
# Build image
docker build -t mcg-agent .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./mcg_agent.db \
  -e JWT_SECRET_KEY=your-secret-key \
  mcg-agent
```

---

## ▶️ Running the Application

### Development Mode

```bash
# Start development server with hot reload
./scripts/start-dev.sh

# Alternative methods:
mcg-agent serve --reload --host 0.0.0.0 --port 8000
uvicorn src.mcg_agent.api.app:app --reload --host 0.0.0.0 --port 8000
```

**Available at:**
- API: `http://localhost:8000`
- Interactive Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Production Mode

```bash
# Start production server with Gunicorn
./scripts/start-prod.sh

# Alternative with custom workers:
mcg-agent serve --workers 4 --host 0.0.0.0 --port 8000
```

---

## 🏥 Health Checks

### Manual Health Check

```bash
# Basic health check
curl http://localhost:8000/health

# Comprehensive health check with script
./scripts/health-check.sh --verbose

# JSON output for monitoring
./scripts/health-check.sh --format json

# Prometheus metrics format
./scripts/health-check.sh --format prometheus
```

### Health Endpoints

- `GET /health/ping` - Basic connectivity
- `GET /health/live` - Liveness probe (Kubernetes)
- `GET /health/ready` - Readiness probe (Kubernetes)  
- `GET /health` - Comprehensive health check

---

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests with coverage
./scripts/run-tests.sh

# Run specific test types
./scripts/run-tests.sh --unit
./scripts/run-tests.sh --integration
./scripts/run-tests.sh --api
./scripts/run-tests.sh --e2e

# Fast mode (no coverage)
./scripts/run-tests.sh --fast

# Keep test database for debugging
./scripts/run-tests.sh --keep-db
```

### Manual Testing

```bash
# Direct pytest
pytest tests/ -v --cov=src/mcg_agent

# Test specific modules
pytest tests/test_auth.py -v
pytest tests/api/ -v

# Test with coverage report
pytest tests/ --cov=src/mcg_agent --cov-report=html
```

---

## 🔐 Security Configuration

### Generate Secure Keys

```bash
# Generate JWT secret key
python -c \"import secrets; print(secrets.token_urlsafe(32))\"

# Generate encryption key
python -c \"import secrets; print(secrets.token_bytes(32).hex())\"
```

### Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use strong, unique passwords** for all accounts
3. **Rotate API keys regularly**
4. **Enable HTTPS in production**
5. **Configure firewall rules** appropriately
6. **Monitor security logs** regularly

---

## 🚀 Production Deployment

### Environment Setup

```bash
# Set production environment
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=WARNING

# Use production database
export DATABASE_URL=postgresql://user:pass@host:5432/mcg_agent

# Configure Redis cluster (if using)
export REDIS_URL=redis://redis-cluster:6379/0
```

### Systemd Service (Linux)

Create `/etc/systemd/system/mcg-agent.service`:

```ini
[Unit]
Description=MCG Agent FastAPI Application
After=network.target

[Service]
Type=exec
User=mcg-agent
Group=mcg-agent
WorkingDirectory=/opt/mcg-agent
Environment=PATH=/opt/mcg-agent/venv/bin
EnvironmentFile=/opt/mcg-agent/.env
ExecStart=/opt/mcg-agent/venv/bin/python -m gunicorn src.mcg_agent.api.app:app --bind 0.0.0.0:8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable mcg-agent
sudo systemctl start mcg-agent
sudo systemctl status mcg-agent
```

### Nginx Configuration

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcg-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcg-agent
  template:
    metadata:
      labels:
        app: mcg-agent
    spec:
      containers:
      - name: mcg-agent
        image: mcg-agent:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: mcg-agent-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 5
```

---

## 🔍 Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check database URL
echo $DATABASE_URL

# Test connection
python -c \"from src.mcg_agent.database.connection import check_db_connection; check_db_connection()\"

# Reinitialize database
./scripts/init-db.sh --force-recreate
```

#### 2. Redis Connection Failed

```bash
# Check Redis URL
echo $REDIS_URL

# Test Redis connection
redis-cli ping

# Check Redis service
sudo systemctl status redis-server
```

#### 3. Import Errors

```bash
# Reinstall dependencies
pip install -e .[dev] --force-reinstall

# Check Python path
python -c \"import sys; print(sys.path)\"

# Check if package is installed
pip show mcg-agent
```

#### 4. Permission Errors

```bash
# Fix file permissions
chmod +x scripts/*.sh

# Fix ownership (if needed)
sudo chown -R $USER:$USER .
```

#### 5. Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill process (replace PID)
kill -9 <PID>

# Or use different port
./scripts/start-dev.sh --port 8080
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# Run with verbose output
./scripts/start-dev.sh --verbose

# Check logs
tail -f logs/mcg-agent.log
```

### Performance Issues

```bash
# Monitor system resources
htop
iostat -x 1

# Check database performance
./scripts/health-check.sh --format json | jq '.details.database'

# Profile application
python -m cProfile -o profile.stats src/mcg_agent/api/app.py
```

---

## 📊 Monitoring & Logging

### Log Files

- **Application Logs**: `logs/mcg-agent.log`
- **Error Logs**: `logs/error.log` 
- **Access Logs**: `logs/access.log`
- **Security Logs**: `logs/security.log`

### Metrics Collection

```bash
# Prometheus metrics
curl http://localhost:8000/monitoring/metrics

# System metrics
curl http://localhost:8000/health | jq '.system'

# Usage analytics
curl http://localhost:8000/monitoring/usage
```

### Health Monitoring

```bash
# Continuous health monitoring
watch -n 30 './scripts/health-check.sh --format json'

# Log health status
./scripts/health-check.sh --format json >> logs/health.log
```

---

## 🛠 Development Tools

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Security scanning
bandit -r src/

# Dependency checking  
safety check
```

### Database Tools

```bash
# Database migrations
mcg-migrate upgrade head

# Database shell
mcg-agent shell

# Backup database
pg_dump mcg_agent > backup.sql

# Restore database
psql mcg_agent < backup.sql
```

### API Testing

```bash
# Interactive API testing
curl -X POST http://localhost:8000/auth/login \
  -H \"Content-Type: application/json\" \
  -d '{\"username\":\"test\",\"password\":\"test\"}'

# Load testing
ab -n 1000 -c 10 http://localhost:8000/health/ping
```

---

## 📚 Additional Resources

### Documentation
- [README.md](./README.md) - Project overview
- [agents.md](./agents.md) - Developer guide  
- [governance.md](./governance.md) - Governance rules
- [API Documentation](http://localhost:8000/docs) - Interactive API docs

### Support
- **Issues**: [GitHub Issues](https://github.com/dansasser/multi-corpus-governance-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dansasser/multi-corpus-governance-agent/discussions)
- **Security**: [Security Policy](./SECURITY.md)

### Contributing
- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) - Code of conduct

---

## ✅ Setup Checklist

- [ ] Clone repository
- [ ] Create virtual environment
- [ ] Install dependencies
- [ ] Configure `.env` file
- [ ] Initialize database
- [ ] Start Redis service
- [ ] Run health checks
- [ ] Start development server
- [ ] Access API documentation
- [ ] Run test suite
- [ ] Configure production environment (if applicable)

---

**🎉 Congratulations!** Your MCG Agent is now set up and ready to use. Visit `http://localhost:8000/docs` to explore the API and start building with the five-agent governance pipeline.