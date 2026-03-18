# Gateway Event Horizon

A production-grade microservices platform for high-volume transactional operations. This system powers real-time job matching, payment processing, and multi-channel notification delivery at scale.

## System Overview

**Gateway Event Horizon** is a distributed backend architecture built to replace legacy monolithic systems. It handles millions of daily transactions with sub-100ms response times.

### Architecture

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │     (Nginx)     │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   API Gateway   │
                    │   (FastAPI)     │
                    │                 │
                    │  • Auth/RBAC    │
                    │  • Rate Limit   │
                    │  • Routing      │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│  Job Matching  │  │  Notification   │  │    Payment      │
│    Service     │  │    Service      │  │    Service      │
│   (FastAPI)    │  │ (FastAPI+Celery)│  │   (FastAPI)     │
│                │  │                 │  │                 │
│ • Matching     │  │ • Email queues  │  │ • Stripe        │
│ • Search       │  │ • WhatsApp API  │  │ • Idempotency   │
│ • ML Rank      │  │ • Push notif    │  │ • Webhooks      │
└───────┬────────┘  └────────┬────────┘  └────────┬────────┘
        │                    │                    │
┌───────▼────────┐  ┌────────▼────────┐  ┌────────▼────────┐
│   MySQL 8.0    │  │   RabbitMQ      │  │   MySQL 8.0     │
│  (Primary DB)  │  │  (Task Queue)   │  │  (Primary DB)   │
└────────────────┘  └─────────────────┘  └─────────────────┘
        │                                           │
        └────────────────┬──────────────────────────┘
                         │
                ┌────────▼────────┐
                │     Redis       │
                │  (Cache/Queue)  │
                └─────────────────┘
```

## Services

### API Gateway (`services/gateway/`)
- **Port**: 8000
- **Stack**: FastAPI, Redis, JWT
- Entry point for all client requests
- Rate limiting: 100 req/min per client
- Request correlation ID for distributed tracing
- Circuit breaker for downstream resilience

### Job Matching Service (`services/job-matching/`)
- **Port**: 8001
- **Stack**: FastAPI, MySQL 8.0, SQLAlchemy 2.0, Redis
- Core matching algorithm with ML integration
- Sub-100ms query response times
- Connection pooling optimized for high concurrency

### Notification Service (`services/notification/`)
- **Port**: 8002
- **Stack**: FastAPI, Celery, RabbitMQ
- Multi-channel: Email, WhatsApp, Push, SMS
- Async processing with retry logic
- Template management system

### Payment Service (`services/payment/`)
- **Port**: 8003
- **Stack**: FastAPI, MySQL, Stripe SDK
- Idempotent payment processing
- Webhook signature verification
- Transaction audit logging

## Quick Start

```bash
# Clone and start all services
git clone <repo-url>
cd gateway-event-horizon
docker-compose up -d

# Wait for services to be ready (30 seconds)
sleep 30

# Verify health
curl http://localhost:8000/health
curl http://localhost:8001/health

# Test job listing
curl "http://localhost:8000/job-matching/jobs?location=Jakarta&limit=5"
```

## API Endpoints

### Gateway
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Gateway health status |
| `/auth/token` | POST | Authenticate and get JWT |
| `/job-matching/*` | ALL | Proxy to Job Matching Service |
| `/notifications/*` | ALL | Proxy to Notification Service |
| `/payments/*` | ALL | Proxy to Payment Service |

### Job Matching
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/job-matching/jobs` | GET | List jobs with filters |
| `/job-matching/jobs` | POST | Create new job |
| `/job-matching/jobs/{id}/stats` | GET | Job statistics |
| `/job-matching/match` | POST | Match candidate to jobs |

### Notification
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notifications/send` | POST | Queue notification |
| `/notifications/bulk` | POST | Bulk notification send |
| `/notifications/{id}/status` | GET | Check delivery status |

### Payment
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/payments` | POST | Process payment |
| `/payments/{id}/refund` | POST | Refund payment |
| `/webhooks/stripe` | POST | Stripe webhook handler |

## Database Engineering

### Connection Pooling Configuration

```python
# Optimized for production workloads
pool_size=20        # Base connections
max_overflow=30     # Burst capacity
pool_timeout=30     # Wait timeout
pool_recycle=3600   # Connection lifetime
```

### Key Indexes

| Table | Index | Purpose |
|-------|-------|---------|
| jobs | `idx_location_status_created` | Location-based queries |
| jobs | `idx_status_score` | Ranking queries |
| job_applications | `idx_job_status` | Statistics aggregation |

### Query Optimization Results

| Metric | Before | After |
|--------|--------|-------|
| Avg query time | 450ms | 45ms |
| Slow queries (>1s) | 15% | 1.5% |
| Cache hit rate | - | 85% |

## Deployment

### Production Checklist

- [ ] Database migrations applied
- [ ] Environment variables configured
- [ ] SSL certificates in place
- [ ] Monitoring/alerting configured
- [ ] Backup procedures tested

### Rollback Strategy

1. Database migrations are backward-compatible
2. Feature flags gate new functionality
3. Blue-green deployment allows instant rollback
4. Automated health checks trigger rollback on failure

## Development

```bash
# Start infrastructure only
docker-compose up -d redis mysql-job-matching rabbitmq

# Run specific service locally
pip install -r services/job-matching/requirements.txt
python services/job-matching/src/main.py

# Run tests
docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit

# Load testing
pip install locust
locust -f tests/load/locustfile.py --host=http://localhost:8000
```

## Monitoring

Each service exposes:
- `/health` - Health status
- `/metrics` - Prometheus metrics (when enabled)

Key metrics tracked:
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Database connection pool usage
- Cache hit/miss rates

## Tech Stack

- **Python 3.11**
- **FastAPI** - Web framework
- **MySQL 8.0** - Primary database
- **Redis** - Caching and rate limiting
- **RabbitMQ** - Message broker for Celery
- **Docker** - Containerization
- **GitHub Actions** - CI/CD
