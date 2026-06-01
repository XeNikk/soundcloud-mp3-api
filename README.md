# SoundCloud Audio Stream API

Production-ready FastAPI service for streaming and downloading audio from SoundCloud tracks as MP3 files. Built with containerization, logging, rate limiting, and comprehensive monitoring in mind.

## Features

- 🎵 **Stream & Download** - Download SoundCloud tracks as high-quality MP3
- 🎼 **Single Track Support** - Dedicated endpoint for individual tracks (no playlists)
- 🐳 **Fully Containerized** - Docker & Docker Compose ready for instant deployment
- ⚙️ **Highly Configurable** - Environment variables for all settings
- 🧹 **Automatic Cleanup** - Configurable TTL with periodic background cleanup
- 📊 **Comprehensive Logging** - Debug production issues with detailed logging
- 🚦 **Rate Limiting** - Protect API from abuse (10 requests/minute per IP)
- 💚 **Health Checks** - Built-in `/health` endpoint for orchestration & monitoring
- 📚 **Interactive Docs** - Auto-generated Swagger UI and ReDoc
- 🔄 **Resilient** - Auto-restart and graceful shutdown handling

## System Requirements

### Docker (Recommended)
- Docker Engine 20.10+
- Docker Compose 1.29+

### Local Development
- Python 3.11+
- FFmpeg 4.0+
- pip or poetry

## Quick Start

### Option 1: Docker Compose (Fastest)

```bash
# Clone the repository
git clone https://github.com/XeNikk/soundcloud-mp3-api.git
cd soundcloud-mp3-api

# Copy environment file
cp .env.example .env

# Start the service
docker-compose up --build
```

The API will be available at `http://localhost:7583`

### Option 2: Docker CLI

```bash
docker build -t soundcloud-mp3-api:latest .

docker run -d \
  --name soundcloud-api \
  -p 7583:7583 \
  -e PORT=7583 \
  -e LOG_LEVEL=INFO \
  -v ./downloads:/app/downloads \
  --restart unless-stopped \
  soundcloud-mp3-api:latest
```

### Option 3: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env from example
cp .env.example .env

# Run the application
python main.py
```

## Configuration

### Environment Variables

All configuration is managed via environment variables. Copy `.env.example` to `.env` and customize:

```bash
# Server Configuration
PORT=7583                          # API port (default: 7583)
LOG_LEVEL=INFO                     # Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL

# File Management
TTL_SECONDS=86400                  # File Time-To-Live in seconds (default: 86400 = 24 hours)
CLEANUP_INTERVAL_MINUTES=60        # Cleanup check interval (default: 60 = 1 hour)
```

### Runtime Configuration Examples

**Using Docker Compose:**
```bash
# Custom port and cleanup interval
PORT=8000 CLEANUP_INTERVAL_MINUTES=30 docker-compose up
```

**Using Docker CLI:**
```bash
docker run -e PORT=8000 \
           -e LOG_LEVEL=DEBUG \
           -e CLEANUP_INTERVAL_MINUTES=30 \
           -p 8000:8000 \
           soundcloud-mp3-api
```

**Using Python directly:**
```bash
export PORT=8000
export LOG_LEVEL=DEBUG
python main.py
```

## API Reference

### Health Check Endpoint

**Endpoint:** `GET /health`

**Purpose:** Monitor service health (useful for Docker health checks, Kubernetes liveness probes)

**Response:**
```json
{
  "status": "ok",
  "service": "soundcloud-mp3-api"
}
```

**Example:**
```bash
curl http://localhost:7583/health
```

### Download/Stream Endpoint

**Endpoint:** `GET /download/{url:path}`

**Rate Limit:** 10 requests per minute per IP address

**Parameters:**
- `url` (required) - Full SoundCloud track URL

**Returns:**
- `200 OK` - MP3 file stream (audio/mpeg)
- `400 Bad Request` - Invalid URL, playlist, or private track
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

**Examples:**

```bash
# Basic download
curl -X GET "http://localhost:7583/download/https://soundcloud.com/user/track-name" -o track.mp3

# With custom headers
curl -X GET "http://localhost:7583/download/https://soundcloud.com/user/track-name" \
  -H "User-Agent: MyApp/1.0" \
  -o track.mp3

# In browser (direct stream)
http://localhost:7583/download/https://soundcloud.com/user/track-name
```

### Interactive API Documentation

- **Swagger UI:** http://localhost:7583/docs
- **ReDoc:** http://localhost:7583/redoc

Test endpoints directly from the browser!

## File Storage & Cleanup

### Storage Location
- Downloaded MP3 files are stored in the `downloads/` directory
- Volume is mounted at `/app/downloads` in container

### Automatic Cleanup
- Files automatically expire after TTL (default: 24 hours)
- Cleanup job runs at configurable intervals (default: 1 hour)
- Re-downloading a file refreshes its TTL
- Useful for production to prevent disk space issues

### Manual Operations

```bash
# List stored files
docker-compose exec api ls -lh downloads/

# Check disk usage
docker-compose exec api du -sh downloads/

# Manual cleanup
docker-compose exec api rm -rf downloads/*

# View logs
docker-compose logs -f api
```

## Monitoring & Logging

### Log Levels

```bash
# Development (verbose)
LOG_LEVEL=DEBUG

# Production (balanced)
LOG_LEVEL=INFO

# Production (minimal)
LOG_LEVEL=WARNING
```

### Log Examples

```
INFO: Starting up - creating cleanup task
INFO: Download request for: https://soundcloud.com/user/trac...
INFO: File exists, serving from cache: 123456789.mp3
INFO: Cleanup: Deleted 5 expired files
WARNING: Playlist attempt: https://soundcloud.com/user/playlist...
ERROR: Download error for https://soundcloud.com/user/track: Track not found
```

### Docker Compose Logging

```bash
# View all logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f api

# View last 100 lines
docker-compose logs api --tail=100
```

## Deployment

### Production Checklist

- [ ] Copy `.env.example` to `.env` and configure
- [ ] Set `LOG_LEVEL=INFO` (not DEBUG)
- [ ] Configure `TTL_SECONDS` and `CLEANUP_INTERVAL_MINUTES` based on disk capacity
- [ ] Set up volume persistence for `downloads/` directory
- [ ] Enable Docker restart policy (`unless-stopped`)
- [ ] Monitor `/health` endpoint for uptime
- [ ] Set up log rotation via Docker logging driver
- [ ] Test rate limiting with `ab` or `wrk`

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: soundcloud-mp3-api
spec:
  replicas: 2
  template:
    spec:
      containers:
      - name: api
        image: soundcloud-mp3-api:latest
        ports:
        - containerPort: 7583
        env:
        - name: PORT
          value: "7583"
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /health
            port: 7583
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 7583
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Project Structure

```
.
├── main.py                 # FastAPI application with all endpoints
├── Dockerfile              # Multi-stage Docker image build
├── docker-compose.yml      # Docker Compose configuration
├── requirements.txt        # Python dependencies (pinned versions)
├── .env.example            # Environment configuration template
├── .gitignore             # Git ignore rules
├── downloads/             # Downloaded MP3 files (auto-cleanup)
└── README.md              # This file
```

## Limitations & Constraints

- ❌ **Playlists not supported** - API accepts single track URLs only
- ❌ **No batch operations** - One track per request
- ⚠️ **Rate limited** - 10 requests per minute per IP
- ⚠️ **Private/deleted tracks** - Returns 400 error if unavailable
- ⚠️ **SoundCloud ToS** - Respect SoundCloud terms of service
- ⚠️ **Copyright** - Ensure compliance with copyright laws in your jurisdiction

## Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Framework** | FastAPI | 0.104.1 |
| **Server** | Uvicorn | 0.24.0 |
| **Download** | yt-dlp | >=2024.1.0 |
| **Audio** | FFmpeg | Latest |
| **Rate Limiting** | Built-in | - |
| **Container** | Docker | 20.10+ |
| **Python** | CPython | 3.11 |

## Troubleshooting

### Docker Desktop Won't Start
```bash
# Restart Docker daemon
docker system prune -a
# Or restart Docker Desktop from system tray
```

### Port Already in Use
```bash
# Check what's using port 7583
lsof -i :7583

# Or use different port
PORT=8000 docker-compose up
```

### Rate Limit Exceeded
```
HTTP 429 Too Many Requests
```
Wait before making new requests or increase `docker-compose up` timeout.

### Files Not Cleaning Up
```bash
# Check cleanup logs
docker-compose logs api | grep Cleanup

# Manual cleanup
docker-compose exec api rm -rf downloads/*

# Reduce CLEANUP_INTERVAL_MINUTES for more frequent checks
CLEANUP_INTERVAL_MINUTES=10 docker-compose up
```

### Out of Disk Space
```bash
# Check usage
docker-compose exec api du -sh downloads/

# Reduce TTL_SECONDS
TTL_SECONDS=43200 docker-compose up  # 12 hours instead of 24
```

## Contributing

Contributions welcome! Feel free to submit issues and pull requests.

## Security Notes

- Rate limiting helps prevent DDoS attacks
- Health checks allow graceful service discovery
- Logging enables audit trails for debugging
- Environment-based configuration prevents hardcoded secrets

## License

MIT License - See LICENSE file for details

---

**Made with ❤️**

For issues and feature requests: [GitHub Issues](https://github.com/XeNikk/soundcloud-mp3-api/issues)

This project is provided as-is. Respect SoundCloud ToS and artist copyrights.