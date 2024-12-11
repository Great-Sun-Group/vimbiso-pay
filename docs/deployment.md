# VimbisoPay Deployment Documentation

## Infrastructure Overview

VimbisoPay is deployed on AWS using a containerized architecture with the following key components:

### Core Infrastructure
- **VPC & Networking**: Multi-AZ setup with public and private subnets
- **ECS (Elastic Container Service)**: Running containerized applications
- **ALB (Application Load Balancer)**: For load balancing and SSL termination
- **EFS (Elastic File System)**: For persistent storage
- **Route53**: DNS management and health checks
- **ECR (Elastic Container Registry)**: For storing Docker images
- **CloudWatch**: For logging and monitoring

### Security Features
- WAF (Web Application Firewall) protection
- SSL/TLS encryption
- Private subnets for application containers
- Security groups for network isolation
- IAM roles with least privilege access

### High Availability Features
- Multi-AZ deployment
- Auto-scaling based on CPU and memory metrics
- Health checks and automatic recovery
- Load balancing across multiple containers

## Local Development Setup

### Prerequisites
- Docker and Docker Compose
- Make
- AWS CLI (for deployment)

### Starting Local Development
1. Clone the repository
2. Copy `.env.example` to `.env` and configure environment variables
3. Run development environment:
   ```bash
   make dev  # Build and start services
   ```

4. Access the application at http://localhost:8000

### Local Development Commands
```bash
make dev         # Build and start development environment (combined command)
make prod        # Build and start production environment (combined command)

# Individual commands if needed:
make dev-build   # Build development environment
make dev-up      # Start development server
make dev-down    # Stop development server
make prod-build  # Build production environment
make prod-up     # Start production server
make prod-down   # Stop production server
```

## Deployment Process

### Continuous Deployment
The application uses GitHub Actions for automated deployments:

1. **Trigger**: Push to `stage` branch or manual workflow dispatch
2. **Environments**:
   - Staging: `stage.whatsapp.vimbisopay.africa`
   - Production: `whatsapp.vimbisopay.africa`

### Deployment Steps
1. **Infrastructure Setup**:
   - Initializes Terraform backend
   - Deploys base infrastructure (VPC, ECS, etc.)
   - Sets up SSL certificates and DNS

2. **Application Deployment**:
   - Builds Docker image
   - Pushes to ECR
   - Updates ECS service
   - Performs health checks

### Deployment Monitoring
The deployment process includes extensive health checks:
- Container health status
- Application health endpoint
- Service stability checks
- Automatic log collection on failures

## Environment Configuration

### Required Environment Variables
```
DJANGO_SECRET              # Django secret key
DJANGO_ENV                 # Environment (development/production)
DEBUG                      # Debug mode (True/False)
MYCREDEX_APP_URL          # Credex core API URL
CLIENT_API_KEY            # API client key
WHATSAPP_API_URL          # WhatsApp API URL
WHATSAPP_ACCESS_TOKEN     # WhatsApp access token
WHATSAPP_PHONE_NUMBER_ID  # WhatsApp phone number ID
WHATSAPP_BUSINESS_ID      # WhatsApp business ID
WHATSAPP_REGISTRATION_FLOW_ID         # Registration flow ID
WHATSAPP_COMPANY_REGISTRATION_FLOW_ID # Company registration flow ID
```

### AWS Configuration
Required AWS permissions are defined in `terraform/vimbisopay-permissions.json`

## Common Operations

### Viewing Logs
```bash
# View ECS service logs
aws logs get-log-events \
  --log-group-name "/ecs/vimbiso-pay-[environment]" \
  --log-stream-name "[stream-name]"
```

### Scaling the Application
- Automatic scaling is configured based on:
  - CPU utilization (threshold: 80%)
  - Memory utilization (threshold: 80%)
  - Request count per target

### Database Backups
- EFS backups are automated with 30-day retention
- Backup policies are managed through AWS Backup

### SSL Certificate Renewal
- Managed automatically through ACM
- DNS validation is automated

## Monitoring and Maintenance

### Health Checks
- Application endpoint: `/health/`
- ALB health checks
- Route53 health checks
- Container health checks

### Monitoring Points
1. **CloudWatch Dashboards**:
   - ECS cluster metrics
   - Application logs
   - ALB metrics
   - Container insights

2. **Alerts**:
   - High CPU/Memory utilization
   - Failed health checks
   - Error rate spikes
   - Failed deployments

### Performance Optimization
- ECS task sizing:
  - CPU: Based on environment configuration
  - Memory: Based on environment configuration
- Auto-scaling configuration:
  - Minimum capacity: 2 tasks
  - Maximum capacity: 4 tasks
  - Scale-out on 80% resource utilization

### Troubleshooting
1. **Deployment Issues**:
   - Check GitHub Actions logs
   - Review ECS service events
   - Inspect container logs
   - Verify health check responses

2. **Application Issues**:
   - Check application logs in CloudWatch
   - Verify EFS mount points
   - Check Redis connectivity
   - Validate environment variables

3. **Infrastructure Issues**:
   - Review Terraform state
   - Check AWS service health
   - Verify security group rules
   - Validate IAM permissions

## Security Considerations

### Network Security
- Private subnets for application containers
- WAF rules for request filtering
- Security groups for network isolation
- SSL/TLS encryption for all traffic

### Data Security
- Encrypted EFS volumes
- Encrypted ECR repositories
- Secure environment variable handling
- Regular security patches

### Access Control
- IAM roles with least privilege
- No direct SSH access to containers
- Restricted network access
- Environment-specific credentials

## Backup and Recovery

### Automated Backups
- EFS: Daily backups with 30-day retention
- ECR: Image retention policy (20 images)
- Terraform state: Versioned S3 bucket

### Disaster Recovery
1. Infrastructure can be recreated using Terraform
2. Data can be restored from EFS backups
3. Application can be rebuilt from ECR images
4. DNS can be updated through Route53
