# MarketBridge Deployment Guide

This guide covers deployment options for the MarketBridge system with comprehensive logging.

## Quick Start

### 1. Development Mode

```bash
# Start the combined server (WebSocket + Web Server)
./scripts/start_server.sh

# Or manually:
python run_server.py
```

**Accessible at:**

- Web Interface: http://localhost:8080
- WebSocket API: ws://localhost:8765
- Health Check: http://localhost:8080/health
- Statistics: http://localhost:8080/stats

### 2. Docker Deployment

```bash
# Build and run with Docker Compose
cd docker
docker-compose up --build

# Or with production nginx proxy:
docker-compose --profile production up --build
```

## Server Components

### Combined Server

- **IBWebSocketBridge**: Connects to Interactive Brokers and provides WebSocket API
- **WebServer**: Serves the web frontend and provides HTTP endpoints
- **Comprehensive Logging**: Structured logging to both console and disk

### Ports

- **8080**: Web server (frontend + API)
- **8765**: WebSocket server (real-time data)
- **7497**: Interactive Brokers TWS/Gateway connection

## Logging System

### Log Files (in `logs/` directory)

1. **`combined_server.log`**: Main server coordination logs
1. **`webserver.log`**: Web server detailed logs
1. **`access.log`**: HTTP access logs (Apache format)
1. **`error.log`**: Web server error logs
1. **`ib_bridge.log`**: Interactive Brokers connection logs

### Log Rotation

- **Automatic rotation** when files reach 10MB (web) or 50MB (access)
- **5-10 backup files** retained per log type
- **UTF-8 encoding** for international character support

### Console Output

- **Real-time logging** to stdout/stderr
- **Structured format** with timestamps, log levels, and file locations
- **Color coding** in development mode

## Configuration

### Command Line Options

```bash
python run_server.py --help

# Common options:
--ib-host 127.0.0.1          # IB TWS/Gateway host
--ib-port 7497               # IB TWS/Gateway port
--ws-port 8765               # WebSocket server port
--web-host localhost         # Web server host
--web-port 8080              # Web server port
--web-root ./web/public      # Static files directory
--log-dir ./logs             # Log files directory
--no-cors                    # Disable CORS headers
```

### Environment Variables

```bash
export IB_HOST=127.0.0.1
export IB_PORT=7497
export WS_PORT=8765
export WEB_HOST=0.0.0.0
export WEB_PORT=8080
export LOG_DIR=/var/log/marketbridge
```

## Production Deployment

### 1. Systemd Service

Create `/etc/systemd/system/marketbridge.service`:

```ini
[Unit]
Description=MarketBridge Trading Server
After=network.target

[Service]
Type=simple
User=marketbridge
Group=marketbridge
WorkingDirectory=/opt/marketbridge
ExecStart=/opt/marketbridge/.venv/bin/python run_server.py --web-host 0.0.0.0
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable marketbridge
sudo systemctl start marketbridge
sudo journalctl -u marketbridge -f  # View logs
```

### 2. Docker Production

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  marketbridge:
    image: marketbridge:latest
    restart: unless-stopped
    ports:
      - "8080:8080"
      - "8765:8765"
    volumes:
      - /var/log/marketbridge:/app/logs
      - /etc/marketbridge:/app/config
    environment:
      - PYTHONUNBUFFERED=1
      - WEB_HOST=0.0.0.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - marketbridge
```

### 3. Reverse Proxy (Nginx)

The included `nginx.conf` provides:

- **SSL termination** (configure certificates)
- **Rate limiting** for API and static content
- **Gzip compression** for better performance
- **Security headers** (XSS protection, CSRF protection)
- **Static file caching** with proper cache headers
- **WebSocket proxy** for real-time connections

## Security Considerations

### 1. Network Security

- **Firewall rules**: Only allow necessary ports (80, 443, 8080, 8765)
- **VPN/Private network**: For IB TWS connections
- **SSL/TLS**: Use HTTPS in production (configure nginx)

### 2. Application Security

- **CORS configuration**: Restrict origins in production
- **Rate limiting**: Included in nginx configuration
- **Input validation**: Built into WebSocket handlers
- **No credential storage**: System doesn't store IB credentials

### 3. Data Security

- **Log sanitization**: No sensitive data logged
- **Secure headers**: Content Security Policy, XSS protection
- **Path traversal protection**: File serving security checks

## Monitoring

### 1. Health Checks

**GET /health**

```json
{
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "timestamp": "2024-01-15T10:30:00",
  "stats": {
    "requests_total": 1250,
    "active_connections": 3
  }
}
```

**GET /stats**

```json
{
  "uptime_seconds": 3600.5,
  "uptime_human": "1h 0m 0s",
  "requests_total": 1250,
  "requests_by_method": {"GET": 1100, "POST": 150},
  "requests_by_status": {"200": 1200, "404": 50},
  "bytes_served": 5242880,
  "active_connections": 3
}
```

### 2. Log Monitoring

**ELK Stack Integration:**

```bash
# Filebeat configuration for log shipping
filebeat.inputs:
- type: log
  paths:
    - /var/log/marketbridge/*.log
  fields:
    service: marketbridge
    environment: production
```

**Prometheus Metrics** (can be added):

- Request rate and response time
- WebSocket connection count
- IB connection status
- Error rates by type

### 3. Alerting

Monitor for:

- **Service health**: Health check failures
- **IB connectivity**: Connection drops to TWS/Gateway
- **High error rates**: 5xx responses or exceptions
- **Resource usage**: Memory, CPU, disk space
- **Log errors**: Critical errors in application logs

## Backup & Recovery

### 1. Configuration Backup

- Server configuration files
- SSL certificates
- Environment configurations

### 2. Log Archival

- Automatic log rotation configured
- Consider log aggregation service
- Backup critical error logs

### 3. Disaster Recovery

- **Infrastructure as Code**: Docker images and compose files
- **Configuration management**: Environment variables and configs
- **Monitoring setup**: Health checks and alerting rules

## Performance Optimization

### 1. Web Server

- **Static file caching**: Configured in nginx
- **Gzip compression**: Reduces bandwidth usage
- **Connection pooling**: Built into aiohttp

### 2. WebSocket Performance

- **Message batching**: For high-frequency updates
- **Connection management**: Automatic cleanup of dead connections
- **Memory management**: Bounded message queues

### 3. System Resources

- **Log rotation**: Prevents disk space issues
- **Memory monitoring**: Track application memory usage
- **Connection limits**: Configure appropriate limits

## Troubleshooting

### Common Issues

1. **Cannot connect to IB TWS/Gateway**

   - Check IB TWS is running and API enabled
   - Verify host/port configuration
   - Check firewall settings

1. **WebSocket connections failing**

   - Verify port 8765 is accessible
   - Check for proxy/firewall blocking WebSockets
   - Review nginx WebSocket proxy configuration

1. **Frontend not loading**

   - Check web server is running on port 8080
   - Verify static files exist in `web/public/`
   - Check nginx configuration if using reverse proxy

1. **High memory usage**

   - Check for memory leaks in market data handling
   - Review log file sizes and rotation
   - Monitor WebSocket connection counts

### Debug Mode

```bash
# Enable debug logging
python run_server.py --log-level DEBUG

# Or set environment variable
export LOG_LEVEL=DEBUG
```

### Log Analysis

```bash
# Monitor real-time logs
tail -f logs/combined_server.log

# Search for errors
grep -i error logs/*.log

# Analyze access patterns
awk '{print $1}' logs/access.log | sort | uniq -c | sort -nr

# Monitor WebSocket connections
grep "WebSocket" logs/webserver.log | tail -20
```
