# Vimbiso Pay Deployment Guide

This document outlines the deployment process and infrastructure for the Vimbiso Pay application.

## Infrastructure Overview

The application is deployed on AWS using:
- ECS Fargate for container orchestration
- Application Load Balancer for routing and SSL termination
- ECR for container registry
- CloudWatch for logging and monitoring
- S3 and DynamoDB for Terraform state management

### Environments

Two deployment environments are supported:
1. Staging (stage.mycredex.dev)
   - Moderate resource allocation
   - Used for pre-production testing
   - Connects to staging Credex Core API

2. Production (mycredex.app)
   - Higher resource allocation
   - Production-grade configuration
   - Connects to production Credex Core API

## Prerequisites

1. AWS Access:
   - AWS access key and secret with appropriate permissions
   - Access to the af-south-1 region

2. GitHub Repository Access:
   - Write access to the repository
   - Ability to manage GitHub Actions secrets

3. Required Secrets:
   ```
   # AWS Configuration
   AWS_ACCESS_KEY
   AWS_SECRET_ACCESS_KEY

   # Django Configuration
   DJANGO_SECRET

   # Credex Core API
   MYCREDEX_APP_URL

   # WhatsApp Integration
   WHATSAPP_BOT_API_KEY
   WHATSAPP_API_URL
   WHATSAPP_ACCESS_TOKEN
   WHATSAPP_PHONE_NUMBER_ID
   ```

## Deployment Process

### 1. Infrastructure Deployment

The infrastructure is deployed using the `connectors.yml` workflow:

1. Navigate to Actions → Deploy Infrastructure
2. Select the branch:
   - `stage` for staging environment
   - `prod` for production environment
3. Run workflow

This deploys:
- VPC and networking
- Load balancer and target groups
- Security groups
- IAM roles
- ECR repository

### 2. Application Deployment

The application is deployed using the `app.yml` workflow:

1. Navigate to Actions → Deploy Application
2. Select the branch:
   - `stage` for staging environment
   - `prod` for production environment
3. Run workflow

This performs:
- Docker image build
- ECR push
- ECS service update
- Deployment monitoring

## Infrastructure Details

### Networking

- VPC with public and private subnets
- NAT gateways for private subnet internet access
- Application Load Balancer in public subnets
- ECS tasks in private subnets

### Container Configuration

- Port 8000 exposed for Django application
- Health check at /health/
- Environment variables injected via ECS task definition

### Auto Scaling

Staging:
```json
{
  "min_capacity": 2,
  "max_capacity": 4,
  "cpu_threshold": 80,
  "memory_threshold": 80
}
```

Production:
```json
{
  "min_capacity": 2,
  "max_capacity": 6,
  "cpu_threshold": 75,
  "memory_threshold": 75
}
```

## Monitoring and Logs

1. CloudWatch Logs:
   - Log group: /ecs/vimbiso-pay-{environment}
   - Contains application and ECS logs

2. Health Checks:
   - ALB health check at /health/
   - Container health check via curl
   - ECS service health monitoring

3. Metrics:
   - CPU and memory utilization
   - Request count and latency
   - 5xx error rate

## Troubleshooting

### Common Issues

1. Deployment Failures:
   - Check ECS task logs in CloudWatch
   - Verify environment variables
   - Check container health check
   - Verify security group rules

2. Health Check Failures:
   - Verify /health/ endpoint is responding
   - Check ALB target group settings
   - Review security group rules

3. Auto Scaling Issues:
   - Review CloudWatch metrics
   - Check scaling policy thresholds
   - Verify ECS service configuration

### Rollback Process

1. Infrastructure:
   ```bash
   # Revert to previous state
   terraform plan -target=module.connectors -out=tfplan
   terraform apply tfplan
   ```

2. Application:
   ```bash
   # Revert to previous image
   aws ecs update-service --cluster vimbiso-pay-cluster-{env} \
     --service vimbiso-pay-service-{env} \
     --task-definition {previous-task-def}
   ```

## Security Considerations

1. Network Security:
   - Private subnets for ECS tasks
   - Security groups limit access
   - SSL/TLS termination at ALB

2. Authentication:
   - WhatsApp API tokens in ECS secrets
   - Django secret managed via ECS
   - AWS IAM roles for service access

3. Monitoring:
   - CloudWatch alarms for errors
   - Access logging enabled
   - Security group changes tracked

## Maintenance

### Regular Tasks

1. ECR Cleanup:
   ```bash
   # Remove untagged images
   aws ecr list-images --repository-name vimbiso-pay-{env} \
     --filter tagStatus=UNTAGGED \
     --query 'imageIds[*]' --output json > untagged.json
   aws ecr batch-delete-image --repository-name vimbiso-pay-{env} \
     --image-ids file://untagged.json
   ```

2. Log Retention:
   - CloudWatch logs retained for 30 days
   - Consider archiving important logs

3. SSL Certificate:
   - Auto-renewed via ACM
   - Monitor renewal status

### Backup Strategy

1. Infrastructure State:
   - S3 bucket versioning enabled
   - DynamoDB point-in-time recovery
   - Regular state backups recommended

2. Application Data:
   - SQLite database backed up with ECS task
   - Consider implementing automated backups

## Future Improvements

1. Monitoring:
   - Add custom CloudWatch dashboards
   - Implement better error tracking
   - Set up automated alerts

2. Performance:
   - Implement caching strategy
   - Optimize container configuration
   - Fine-tune auto-scaling

3. Security:
   - Implement WAF rules
   - Add rate limiting
   - Enhance logging and auditing
