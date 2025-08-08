# icotes Docker Deployment Guide

## Docker Hub Repository
**Repository**: https://hub.docker.com/r/penthoy/icotes

## Quick Start

### Single Instance Deployment
```bash
# Pull and run the latest image
docker run -d \
  --name icotes \
  -p 8000:8000 \
  penthoy/icotes:latest

# Check if it's running
docker ps
curl http://localhost:8000/health
```

### Multi-Instance SaaS Deployment
```bash
# Using docker-compose
git clone <your-repo>
cd icotes
docker compose up -d

# Or manually with environment variables
docker run -d \
  --name icotes-instance1 \
  -p 8001:8000 \
  -e SAAS_MODE=true \
  -e INSTANCE_ID=instance-1 \
  -e API_KEY=your-api-key \
  penthoy/icotes:latest
```

## Available Tags
- `penthoy/icotes:latest` - Latest stable build
- `penthoy/icotes:v1.0` - Version 1.0 release

## Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SAAS_MODE` | Enable SaaS multi-tenant mode | `false` | No |
| `INSTANCE_ID` | Unique identifier for SaaS instances | - | SaaS only |
| `API_KEY` | Authentication key for SaaS mode | - | SaaS only |

## Health Check
All instances expose a health check endpoint at `/health`:
```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "services": {
    "icpy": true,
    "terminal": true,
    "clipboard": {
      "read": false,
      "write": true,
      "history": true,
      "multi_format": false
    }
  }
}
```

## Ports
- **8000**: Main application port (HTTP)
  - Serves both frontend React app and backend FastAPI
  - Single-port architecture for simplified deployment

## Resource Requirements
- **Minimum**: 256MB RAM, 0.25 CPU
- **Recommended**: 1GB RAM, 1.0 CPU
- **Storage**: ~1.5GB for Docker image

## Production Deployment Examples

### Docker Compose (Recommended)
```yaml
version: '3.8'
services:
  icotes:
    image: penthoy/icotes:latest
    ports:
      - "8000:8000"
    environment:
      - SAAS_MODE=true
      - INSTANCE_ID=prod-instance
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 1g
          cpus: '1.0'
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: icotes
spec:
  replicas: 3
  selector:
    matchLabels:
      app: icotes
  template:
    metadata:
      labels:
        app: icotes
    spec:
      containers:
      - name: icotes
        image: penthoy/icotes:latest
        ports:
        - containerPort: 8000
        env:
        - name: SAAS_MODE
          value: "true"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Docker Swarm
```bash
# Create a service
docker service create \
  --name icotes \
  --publish 8000:8000 \
  --replicas 3 \
  --env SAAS_MODE=true \
  penthoy/icotes:latest
```

## Troubleshooting

### Check Container Logs
```bash
docker logs <container-name>
```

### Verify Health
```bash
# Container should show (healthy) status
docker ps

# Manual health check
curl -f http://localhost:8000/health || echo "Health check failed"
```

### Common Issues
1. **Port conflicts**: Change host port mapping (`-p HOST_PORT:8000`)
2. **Health check timeout**: Wait 30-40 seconds for application startup
3. **Resource constraints**: Ensure sufficient memory allocation

## Development and Testing
For local development, you can also build from source:
```bash
git clone <your-repo>
cd icotes
docker build -t icotes:local .
docker run -p 8000:8000 icotes:local
```

## Support
- Repository: https://github.com/penthoy/icotes
- Docker Hub: https://hub.docker.com/r/penthoy/icotes
- Issues: https://github.com/penthoy/icotes/issues
