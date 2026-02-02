# AgentTrace Deployment Guide

Production deployment guide for AgentTrace.

## Overview

AgentTrace can be deployed in several ways:
- **Docker Compose** - Simple single-node deployment
- **Kubernetes** - Scalable, production-grade deployment
- **Managed Services** - Using cloud databases and container services

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB storage minimum
- PostgreSQL 16+ with TimescaleDB extension

## Docker Compose Deployment

The simplest way to deploy AgentTrace for production.

### Quick Start

```bash
# Clone repository
git clone https://github.com/jimmybentley/AgentTrace.git
cd AgentTrace

# Start all services
docker compose up -d

# Check status
docker compose ps
```

### Production Configuration

Create a `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB: agenttrace
      POSTGRES_USER: agenttrace
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U agenttrace"]
      interval: 10s
      timeout: 5s
      retries: 5

  ingestion:
    build:
      context: .
      dockerfile: Dockerfile.ingestion
    environment:
      DATABASE_URL: postgresql://agenttrace:${DB_PASSWORD}@postgres:5432/agenttrace
      OTLP_HTTP_PORT: 4318
      LOG_LEVEL: INFO
    ports:
      - "4318:4318"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    environment:
      DATABASE_URL: postgresql://agenttrace:${DB_PASSWORD}@postgres:5432/agenttrace
      API_PORT: 8000
      LOG_LEVEL: INFO
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  web:
    build:
      context: ./web
      dockerfile: Dockerfile
    environment:
      VITE_API_URL: http://api:8000
    ports:
      - "3000:80"
    depends_on:
      - api
    restart: unless-stopped

volumes:
  pgdata:
```

### Environment Variables

Create `.env.prod`:

```bash
# Database
DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD

# Ingestion
OTLP_HTTP_PORT=4318
BATCH_SIZE=100
POOL_SIZE=20

# API
API_PORT=8000
CORS_ORIGINS=https://yourdomain.com

# Logging
LOG_LEVEL=INFO

# Optional: External monitoring
PROMETHEUS_ENABLED=true
```

### Start Production Stack

```bash
# Load environment variables
export $(cat .env.prod | xargs)

# Start services
docker compose -f docker-compose.prod.yml up -d

# Run migrations
docker compose exec api alembic upgrade head

# Verify health
curl http://localhost:8000/health
curl http://localhost:4318/health
```

### Reverse Proxy (Nginx)

Configure Nginx for SSL termination:

```nginx
server {
    listen 80;
    server_name agenttrace.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name agenttrace.yourdomain.com;

    ssl_certificate /etc/ssl/certs/agenttrace.crt;
    ssl_certificate_key /etc/ssl/private/agenttrace.key;

    # Web UI
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # OTLP Ingestion
    location /v1/traces {
        proxy_pass http://localhost:4318/v1/traces;
        proxy_http_version 1.1;
        proxy_set_header X-Real-IP $remote_addr;
        client_max_body_size 10M;
    }
}
```

## Kubernetes Deployment

For production-grade scalability and reliability.

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Helm 3+ (optional but recommended)

### Database Setup

Deploy PostgreSQL with TimescaleDB using a Helm chart:

```bash
helm repo add timescale https://charts.timescale.com
helm install agenttrace-db timescale/timescaledb-single \
  --set persistentVolume.size=100Gi \
  --set resources.requests.memory=4Gi \
  --set resources.requests.cpu=2
```

Or use a managed service (AWS RDS, GCP Cloud SQL, Azure Database).

### Deployment Manifests

#### Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agenttrace
```

#### ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agenttrace-config
  namespace: agenttrace
data:
  DATABASE_URL: "postgresql://agenttrace:password@postgres:5432/agenttrace"
  OTLP_HTTP_PORT: "4318"
  API_PORT: "8000"
  LOG_LEVEL: "INFO"
```

#### Secret

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: agenttrace-secret
  namespace: agenttrace
type: Opaque
stringData:
  DB_PASSWORD: "CHANGE_ME"
```

#### Ingestion Deployment

```yaml
# ingestion-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenttrace-ingestion
  namespace: agenttrace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agenttrace-ingestion
  template:
    metadata:
      labels:
        app: agenttrace-ingestion
    spec:
      containers:
      - name: ingestion
        image: agenttrace/ingestion:latest
        ports:
        - containerPort: 4318
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: agenttrace-config
              key: DATABASE_URL
        - name: DB_PASSWORD
          valueFrom:
            secretKeyRef:
              name: agenttrace-secret
              key: DB_PASSWORD
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 4318
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 4318
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: agenttrace-ingestion
  namespace: agenttrace
spec:
  selector:
    app: agenttrace-ingestion
  ports:
  - port: 4318
    targetPort: 4318
  type: ClusterIP
```

#### API Deployment

```yaml
# api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenttrace-api
  namespace: agenttrace
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agenttrace-api
  template:
    metadata:
      labels:
        app: agenttrace-api
    spec:
      containers:
      - name: api
        image: agenttrace/api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: agenttrace-config
              key: DATABASE_URL
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: agenttrace-api
  namespace: agenttrace
spec:
  selector:
    app: agenttrace-api
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP
```

#### Web UI Deployment

```yaml
# web-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agenttrace-web
  namespace: agenttrace
spec:
  replicas: 2
  selector:
    matchLabels:
      app: agenttrace-web
  template:
    metadata:
      labels:
        app: agenttrace-web
    spec:
      containers:
      - name: web
        image: agenttrace/web:latest
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: agenttrace-web
  namespace: agenttrace
spec:
  selector:
    app: agenttrace-web
  ports:
  - port: 80
    targetPort: 80
  type: ClusterIP
```

#### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agenttrace-ingress
  namespace: agenttrace
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - agenttrace.yourdomain.com
    secretName: agenttrace-tls
  rules:
  - host: agenttrace.yourdomain.com
    http:
      paths:
      - path: /v1/traces
        pathType: Prefix
        backend:
          service:
            name: agenttrace-ingestion
            port:
              number: 4318
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: agenttrace-api
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agenttrace-web
            port:
              number: 80
```

### Deploy to Kubernetes

```bash
# Apply manifests
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f ingestion-deployment.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f web-deployment.yaml
kubectl apply -f ingress.yaml

# Check status
kubectl get pods -n agenttrace
kubectl get svc -n agenttrace

# View logs
kubectl logs -f deployment/agenttrace-ingestion -n agenttrace
```

### Horizontal Pod Autoscaling

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agenttrace-ingestion-hpa
  namespace: agenttrace
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agenttrace-ingestion
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Database Configuration

### Connection Pooling

For high throughput, tune connection pool:

```python
# config.py
POOL_SIZE = 20           # Number of persistent connections
POOL_MAX_OVERFLOW = 10   # Additional connections when needed
POOL_TIMEOUT = 30        # Timeout for getting connection
POOL_RECYCLE = 3600      # Recycle connections after 1 hour
```

### TimescaleDB Tuning

Optimize PostgreSQL for AgentTrace:

```sql
-- postgresql.conf
shared_buffers = 4GB
effective_cache_size = 12GB
work_mem = 64MB
maintenance_work_mem = 1GB
max_connections = 200

-- TimescaleDB settings
timescaledb.max_background_workers = 8
```

### Retention Policy

Configure data retention:

```sql
-- Keep 30 days of data
SELECT add_retention_policy('spans', INTERVAL '30 days');

-- Keep 90 days of traces
SELECT add_retention_policy('traces', INTERVAL '90 days');
```

## Monitoring

### Prometheus Integration

The ingestion service exposes metrics at `/metrics`:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'agenttrace-ingestion'
    static_configs:
      - targets: ['agenttrace-ingestion:4318']

  - job_name: 'agenttrace-api'
    static_configs:
      - targets: ['agenttrace-api:8000']
```

### Grafana Dashboard

Import the AgentTrace dashboard (coming soon) or create custom panels:

**Key Metrics:**
- Traces ingested per second
- Average trace duration
- Error rate
- Database connection pool usage
- API response times

### Logging

Configure structured logging:

```yaml
# logging.yaml
version: 1
formatters:
  json:
    class: pythonjsonlogger.jsonlogger.JsonFormatter
handlers:
  console:
    class: logging.StreamHandler
    formatter: json
loggers:
  agenttrace:
    level: INFO
    handlers: [console]
```

## Backup and Recovery

### Database Backup

Use `pg_dump` for backups:

```bash
# Daily backup
pg_dump -h localhost -U agenttrace agenttrace | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore
gunzip -c backup_20240101.sql.gz | psql -h localhost -U agenttrace agenttrace
```

### Kubernetes Backup

Use Velero for Kubernetes backups:

```bash
velero backup create agenttrace-backup --include-namespaces agenttrace
velero restore create --from-backup agenttrace-backup
```

## Security

### SSL/TLS

Always use HTTPS in production:

```bash
# Generate certificates with Let's Encrypt
certbot certonly --standalone -d agenttrace.yourdomain.com
```

### Database Encryption

Enable encryption at rest:

```sql
-- PostgreSQL encryption at rest (requires appropriate filesystem)
ALTER SYSTEM SET ssl = on;
ALTER SYSTEM SET ssl_cert_file = '/etc/ssl/certs/server.crt';
ALTER SYSTEM SET ssl_key_file = '/etc/ssl/private/server.key';
```

### Network Policies

Restrict network access in Kubernetes:

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agenttrace-netpol
  namespace: agenttrace
spec:
  podSelector:
    matchLabels:
      app: agenttrace-api
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: agenttrace-web
    ports:
    - protocol: TCP
      port: 8000
```

## Performance Tuning

### Ingestion Throughput

Increase workers and batch size:

```bash
# uvicorn with multiple workers
uvicorn agenttrace_ingestion.server:app \
  --workers 8 \
  --host 0.0.0.0 \
  --port 4318

# Increase batch size
export BATCH_SIZE=500
```

### Query Optimization

Create indexes for common queries:

```sql
-- Indexes for common filters
CREATE INDEX idx_traces_service_name ON traces(service_name);
CREATE INDEX idx_traces_status ON traces(status);
CREATE INDEX idx_spans_attributes ON spans USING gin(attributes);
```

### Caching

Add Redis for query caching (future feature):

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
```

## Troubleshooting

### High Memory Usage

Check database connections:

```sql
SELECT count(*) FROM pg_stat_activity;
```

Reduce pool size if needed.

### Slow Queries

Enable query logging:

```sql
ALTER SYSTEM SET log_min_duration_statement = 1000; -- Log queries > 1s
```

### Ingestion Errors

Check logs:

```bash
docker compose logs ingestion
kubectl logs -f deployment/agenttrace-ingestion -n agenttrace
```

Common issues:
- Database connection timeout
- Malformed OTLP traces
- Disk space full

## Scaling Guidelines

| Traces/Day | Database Size | CPU | Memory | Nodes |
|------------|---------------|-----|--------|-------|
| < 10k | 10GB | 2 cores | 4GB | 1 |
| 10k - 100k | 50GB | 4 cores | 8GB | 2 |
| 100k - 1M | 200GB | 8 cores | 16GB | 3-5 |
| > 1M | 1TB+ | 16+ cores | 32GB+ | 5-10 |

## Cloud Provider Guides

### AWS

- Use RDS for PostgreSQL with TimescaleDB
- Deploy on ECS or EKS
- Use ALB for load balancing
- Store backups in S3

### GCP

- Use Cloud SQL for PostgreSQL
- Deploy on GKE
- Use Cloud Load Balancing
- Store backups in Cloud Storage

### Azure

- Use Azure Database for PostgreSQL
- Deploy on AKS
- Use Azure Load Balancer
- Store backups in Blob Storage

## Related Documentation

- [Getting Started Guide](getting-started.md) - Initial setup
- [Architecture Overview](architecture.md) - System design
- [API Reference](api-reference.md) - API documentation

## Support

For deployment issues:
- Check [GitHub Issues](https://github.com/jimmybentley/AgentTrace/issues)
- Review deployment logs
- Verify database connectivity
