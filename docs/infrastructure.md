# Infrastructure & Operations

## Core Infrastructure

VimbisoPay runs on AWS with:

### Production Components
- ECS for containerized applications
- Redis for state management
- ALB for load balancing
- Route53 for DNS
- CloudWatch for monitoring

### Security Features
- WAF protection
- SSL/TLS encryption
- Private subnets
- Security groups
- IAM roles
- Redis security

### High Availability
- Multi-AZ deployment
- Auto-scaling
- Health checks
- Load balancing
- Redis persistence

## State Management

### Redis Architecture
- Atomic operations
- AOF persistence
- Memory limits with LRU
- Validation tracking
- Error handling

### Production Settings
```python
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_PRELOAD = True
```

## Monitoring

### Health Checks
- Application endpoint: `/health/`
- Redis ping tests
- Container checks
- Load balancer checks

### Key Metrics
1. **Application**
   - CPU/Memory usage
   - Request rates
   - Error rates
   - Flow progression

2. **Redis**
   - Memory usage
   - Operation latency
   - Connection count
   - Eviction rates

### Alerts
- High resource usage
- Failed health checks
- Error rate spikes
- Redis warnings

### Scaling
- CPU threshold: 80%
- Memory threshold: 80%
- Request count based
- Redis memory based

### Backups
- Redis AOF persistence
- 30-day retention
- Automated backups
- Recovery procedures

### Troubleshooting

#### General Steps
1. Check service health
2. Review application logs
3. Monitor Redis metrics
4. Verify configurations
5. Test connectivity

#### Deployment Issues
When tasks are failing during deployment:

1. **Circuit Breaker Settings**
   - By default, ECS deployment circuit breaker is enabled with automatic rollback
   - For debugging deployment issues, disable rollback in `service.tf`:
     ```hcl
     deployment_circuit_breaker {
       enable   = true
       rollback = false  # Temporarily disable for debugging
     }
     ```
   - This preserves the failed state for investigation
   - **Important**: Re-enable rollback after debugging is complete

2. **Health Check Investigation**
   - Check container health status in ECS console
   - Review CloudWatch logs for both containers
   - Verify EFS mount points and permissions
   - Check Redis connectivity and state

3. **Common Issues**
   - Task termination due to failed health checks
   - EFS mount issues
   - Redis state persistence problems
   - Network connectivity failures
