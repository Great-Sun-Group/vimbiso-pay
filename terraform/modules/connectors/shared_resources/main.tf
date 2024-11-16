# Add us-east-1 provider for CloudFront certificate
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.common_tags, {
    Name = "credex-vpc-${var.environment}"
  })
}

# Fetch AZs in the current region
data "aws_availability_zones" "available" {}

# Create private subnets, each in a different AZ
resource "aws_subnet" "private" {
  count             = var.az_count
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  vpc_id            = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name = "credex-private-subnet-${var.environment}-${count.index + 1}"
  })
}

# Create public subnets, each in a different AZ
resource "aws_subnet" "public" {
  count                   = var.az_count
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, var.az_count + count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  vpc_id                  = aws_vpc.main.id
  map_public_ip_on_launch = true

  tags = merge(var.common_tags, {
    Name = "credex-public-subnet-${var.environment}-${count.index + 1}"
  })
}

# Internet Gateway for the public subnet
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(var.common_tags, {
    Name = "credex-igw-${var.environment}"
  })
}

# Route the public subnet traffic through the IGW
resource "aws_route" "internet_access" {
  route_table_id         = aws_vpc.main.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Create a NAT gateway with an Elastic IP for each private subnet to get internet connectivity
resource "aws_eip" "nat" {
  count      = var.az_count
  vpc        = true
  depends_on = [aws_internet_gateway.main]

  tags = merge(var.common_tags, {
    Name = "credex-eip-${var.environment}-${count.index + 1}"
  })
}

resource "aws_nat_gateway" "main" {
  count         = var.az_count
  subnet_id     = element(aws_subnet.public[*].id, count.index)
  allocation_id = element(aws_eip.nat[*].id, count.index)

  tags = merge(var.common_tags, {
    Name = "credex-nat-${var.environment}-${count.index + 1}"
  })
}

# Create a new route table for the private subnets
resource "aws_route_table" "private" {
  count  = var.az_count
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = element(aws_nat_gateway.main[*].id, count.index)
  }

  tags = merge(var.common_tags, {
    Name = "credex-private-route-table-${var.environment}-${count.index + 1}"
  })
}

# Associate the private subnets with the appropriate route tables
resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = element(aws_subnet.private[*].id, count.index)
  route_table_id = element(aws_route_table.private[*].id, count.index)
}

# Key Pair
resource "aws_key_pair" "credex_key_pair" {
  key_name   = "credex-key-pair-${var.environment}"
  public_key = var.public_key
}

# ALB security group
resource "aws_security_group" "alb" {
  name        = "credex-alb-sg-${var.environment}"
  description = "Controls access to the ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP inbound traffic"
  }

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS inbound traffic"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.common_tags, {
    Name = "credex-alb-sg-${var.environment}"
  })
}

# ECS tasks security group
resource "aws_security_group" "ecs_tasks" {
  name        = "credex-core-ecs-tasks-sg-${var.environment}"
  description = "Allow inbound access from the ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 3000
    to_port         = 3000
    security_groups = [aws_security_group.alb.id]
    description     = "Allow inbound traffic from ALB"
  }

  ingress {
    protocol    = "tcp"
    from_port   = 3000
    to_port     = 3000
    cidr_blocks = [var.vpc_cidr]
    description = "Allow health checks from VPC"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.common_tags, {
    Name = "credex-core-ecs-tasks-sg-${var.environment}"
  })
}

# Neo4j security group
resource "aws_security_group" "neo4j" {
  name        = "credex-neo4j-sg-${var.environment}"
  description = "Security group for Neo4j instances"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 7474
    to_port     = 7474
    cidr_blocks = [var.vpc_cidr]
    description = "Allow Neo4j HTTP"
  }

  ingress {
    protocol    = "tcp"
    from_port   = 7687
    to_port     = 7687
    cidr_blocks = [var.vpc_cidr]
    description = "Allow Neo4j Bolt"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(var.common_tags, {
    Name = "credex-neo4j-sg-${var.environment}"
  })
}

# S3 bucket for docs
resource "aws_s3_bucket" "docs" {
  bucket = "docs.${var.domain}"

  tags = merge(var.common_tags, {
    Name = "docs-${var.environment}"
  })
}

# Add block public access configuration before bucket policy
resource "aws_s3_bucket_public_access_block" "docs" {
  bucket = aws_s3_bucket.docs.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_website_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id
  index_document {
    suffix = "index.html"
  }
}

resource "aws_s3_bucket_policy" "docs" {
  bucket = aws_s3_bucket.docs.id
  depends_on = [aws_s3_bucket_public_access_block.docs]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.docs.arn}/*"
      },
    ]
  })
}

# ACM Certificate for ALB (in current region)
resource "aws_acm_certificate" "credex_cert" {
  domain_name               = var.domain
  subject_alternative_names = ["*.${var.domain}"]
  validation_method         = "DNS"

  tags = merge(var.common_tags, {
    Name = "credex-cert-${var.environment}"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# ACM Certificate for CloudFront (in us-east-1)
resource "aws_acm_certificate" "cloudfront_cert" {
  provider = aws.us_east_1
  
  domain_name               = "docs.${var.domain}"
  validation_method         = "DNS"

  tags = merge(var.common_tags, {
    Name = "credex-cloudfront-cert-${var.environment}"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Get the hosted zone for the domain
data "aws_route53_zone" "domain" {
  name = var.domain_base
}

# Create DNS records for certificate validation (for both certificates)
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in concat(
      [for opt in aws_acm_certificate.credex_cert.domain_validation_options : opt],
      [for opt in aws_acm_certificate.cloudfront_cert.domain_validation_options : opt]
    ) : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.domain.zone_id
}

# Certificate validation for both certificates
resource "aws_acm_certificate_validation" "credex_cert" {
  certificate_arn         = aws_acm_certificate.credex_cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

resource "aws_acm_certificate_validation" "cloudfront_cert" {
  provider = aws.us_east_1
  
  certificate_arn         = aws_acm_certificate.cloudfront_cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# CloudFront distribution for docs
resource "aws_cloudfront_distribution" "docs" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  aliases             = ["docs.${var.domain}"]
  price_class         = "PriceClass_100"

  origin {
    domain_name = aws_s3_bucket_website_configuration.docs.website_endpoint
    origin_id   = "S3-docs.${var.domain}"
    
    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "http-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-docs.${var.domain}"
    viewer_protocol_policy = "redirect-to-https"
    compress              = true

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate_validation.cloudfront_cert.certificate_arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }

  tags = merge(var.common_tags, {
    Name = "docs-cloudfront-${var.environment}"
  })
}

# Application Load Balancer (ALB)
resource "aws_lb" "credex_alb" {
  name               = "credex-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = var.common_tags
}

# Target Group
resource "aws_lb_target_group" "credex_core" {
  name        = "credex-tg-${var.environment}"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    healthy_threshold   = "2"
    interval            = "60"
    protocol            = "HTTP"
    matcher             = "200"
    timeout             = "30"
    path                = "/health"
    unhealthy_threshold = "5"
  }

  tags = var.common_tags
}

# Create Route53 records
resource "aws_route53_record" "alb" {
  zone_id = data.aws_route53_zone.domain.zone_id
  name    = var.domain
  type    = "A"

  alias {
    name                   = aws_lb.credex_alb.dns_name
    zone_id                = aws_lb.credex_alb.zone_id
    evaluate_target_health = true
  }
}

# Update Route53 record for docs to point to CloudFront
resource "aws_route53_record" "docs" {
  zone_id = data.aws_route53_zone.domain.zone_id
  name    = "docs.${var.domain}"
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.docs.domain_name
    zone_id                = aws_cloudfront_distribution.docs.hosted_zone_id
    evaluate_target_health = false
  }
}

# ALB Listener
resource "aws_lb_listener" "credex_listener" {
  load_balancer_arn = aws_lb.credex_alb.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate_validation.credex_cert.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.credex_core.arn
  }
}

# Rule for docs subdomain requests
resource "aws_lb_listener_rule" "docs" {
  listener_arn = aws_lb_listener.credex_listener.arn
  priority     = 100

  condition {
    host_header {
      values = ["docs.${var.domain}"]
    }
  }

  action {
    type = "fixed-response"
    
    fixed_response {
      content_type = "text/plain"
      message_body = "Please visit the docs at https://docs.${var.domain}"
      status_code  = "200"
    }
  }
}

# Rule for root path on main domain
resource "aws_lb_listener_rule" "root_to_docs" {
  listener_arn = aws_lb_listener.credex_listener.arn
  priority     = 90  # Higher priority than default but lower than docs subdomain rule

  condition {
    host_header {
      values = [var.domain]
    }
  }

  condition {
    path_pattern {
      values = ["/$"]  # Exact match for root path only
    }
  }

  action {
    type = "redirect"

    redirect {
      host        = "docs.${var.domain}"
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
      path        = "/"
    }
  }
}

# ECR Repository
resource "aws_ecr_repository" "credex_core" {
  name = "credex-core-${var.environment}"
  
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(var.common_tags, {
    Name = "credex-core-ecr-${var.environment}"
  })
}

# ECS execution role
resource "aws_iam_role" "ecs_execution_role" {
  name = "ecs-execution-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "ecs-execution-role-${var.environment}"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS task role
resource "aws_iam_role" "ecs_task_role" {
  name = "ecs-task-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "ecs-task-role-${var.environment}"
  })
}

# Add CloudWatch Logs permissions to ECS task role
resource "aws_iam_role_policy" "ecs_task_role_policy" {
  name = "ecs-task-role-policy-${var.environment}"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "${aws_cloudwatch_log_group.ecs_logs.arn}:*"
      }
    ]
  })
}

# Add SSM permissions for debugging
resource "aws_iam_role_policy_attachment" "ecs_task_role_ssm" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

# CloudWatch log group
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/credex-core-${var.environment}"
  retention_in_days = 30

  tags = merge(var.common_tags, {
    Name = "/ecs/credex-core-${var.environment}"
  })
}

#############################
# Verification System Storage
#############################

# Main storage bucket for verification photos
# Purpose: Stores all verification-related photos with proper organization and security
# Security: Encrypted at rest, no public access, versioning enabled
# Access Pattern: Write to uploads/, process to processed/, archive to archived/
resource "aws_s3_bucket" "verification_photos" {
  bucket = "credex-verification-photos-${var.environment}"

  tags = merge(var.common_tags, {
    Name = "verification-photos-${var.environment}"
    Purpose = "ID Verification Storage"
    DataClassification = "Sensitive"
  })
}

# Enable versioning to maintain file history and prevent accidental deletions
# Required for: Compliance, data protection, and cross-region replication
resource "aws_s3_bucket_versioning" "verification_photos" {
  bucket = aws_s3_bucket.verification_photos.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Enable server-side encryption for data at rest
# Security: AES-256 encryption for all objects
resource "aws_s3_bucket_server_side_encryption_configuration" "verification_photos" {
  bucket = aws_s3_bucket.verification_photos.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Block all public access for security
# Critical for protecting sensitive verification data
resource "aws_s3_bucket_public_access_block" "verification_photos" {
  bucket = aws_s3_bucket.verification_photos.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Create organized folder structure for different stages of verification
# Structure:
# - uploads/: Raw uploaded files
# - processed/: Validated and processed files
# - archived/: Historical records
# - temp/: Temporary processing files
resource "aws_s3_object" "verification_folders" {
  for_each = toset([
    "uploads/id-documents/",    # Raw ID document uploads
    "uploads/selfies/",         # Raw selfie photo uploads
    "processed/id-documents/",  # Processed and validated ID documents
    "processed/selfies/",       # Processed and validated selfies
    "archived/",               # Historical records
    "temp/"                    # Temporary processing files
  ])

  bucket = aws_s3_bucket.verification_photos.id
  key    = each.key
  source = "/dev/null"  # Empty object for folder creation
}

# Configure lifecycle rules for cost optimization and data management
# Rules:
# 1. Archive uploads after 90 days, delete after 1 year
# 2. Clean temporary files daily
# 3. Move processed files through storage tiers
resource "aws_s3_bucket_lifecycle_configuration" "verification_photos" {
  bucket = aws_s3_bucket.verification_photos.id

  rule {
    id     = "archive-uploads"
    status = "Enabled"

    transition {
      days          = var.verification_photos_retention_days
      storage_class = "GLACIER"
    }

    expiration {
      days = var.verification_photos_expiration_days
    }

    filter {
      prefix = "uploads/"
    }
  }

  rule {
    id     = "clean-temp-folder"
    status = "Enabled"
    
    expiration {
      days = var.verification_temp_retention_days
    }

    filter {
      prefix = "temp/"
    }
  }

  rule {
    id     = "archive-processed"
    status = "Enabled"

    transition {
      days          = var.verification_processed_transition_days
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = var.verification_processed_archive_days
      storage_class = "GLACIER"
    }

    filter {
      prefix = "processed/"
    }
  }
}

# Configure CORS for secure API access
# Restricts access to application domain only
resource "aws_s3_bucket_cors_configuration" "verification_photos" {
  bucket = aws_s3_bucket.verification_photos.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["https://*.${var.domain}"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

# Access logging bucket for audit trail
# Purpose: Store access logs for security and compliance
resource "aws_s3_bucket" "verification_logs" {
  bucket = "credex-verification-logs-${var.environment}"

  tags = merge(var.common_tags, {
    Name = "verification-logs-${var.environment}"
    Purpose = "Access Logging"
    DataClassification = "Audit"
  })
}

# Block public access for logs bucket
resource "aws_s3_bucket_public_access_block" "verification_logs" {
  bucket = aws_s3_bucket.verification_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable encryption for logs
resource "aws_s3_bucket_server_side_encryption_configuration" "verification_logs" {
  bucket = aws_s3_bucket.verification_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Enable access logging for main bucket
resource "aws_s3_bucket_logging" "verification_photos" {
  bucket = aws_s3_bucket.verification_photos.id

  target_bucket = aws_s3_bucket.verification_logs.id
  target_prefix = "access-logs/"
}

# Cross-region backup bucket for disaster recovery
# Located in us-east-1 for geographic redundancy
resource "aws_s3_bucket" "verification_backups" {
  provider = aws.us_east_1
  bucket   = "credex-verification-backups-${var.environment}"

  tags = merge(var.common_tags, {
    Name = "verification-backups-${var.environment}"
    Purpose = "Disaster Recovery"
    DataClassification = "Backup"
  })
}

# Enable versioning for backup bucket
resource "aws_s3_bucket_versioning" "verification_backups" {
  provider = aws.us_east_1
  bucket   = aws_s3_bucket.verification_backups.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Block public access for backup bucket
resource "aws_s3_bucket_public_access_block" "verification_backups" {
  provider = aws.us_east_1
  bucket   = aws_s3_bucket.verification_backups.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable encryption for backup bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "verification_backups" {
  provider = aws.us_east_1
  bucket   = aws_s3_bucket.verification_backups.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# IAM role for S3 replication
resource "aws_iam_role" "verification_replication" {
  name = "verification-replication-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for S3 replication permissions
resource "aws_iam_role_policy" "verification_replication" {
  name = "verification-replication-policy-${var.environment}"
  role = aws_iam_role.verification_replication.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetReplicationConfiguration",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.verification_photos.arn
        ]
      },
      {
        Action = [
          "s3:GetObjectVersionForReplication",
          "s3:GetObjectVersionAcl",
          "s3:GetObjectVersionTagging"
        ]
        Effect = "Allow"
        Resource = [
          "${aws_s3_bucket.verification_photos.arn}/*"
        ]
      },
      {
        Action = [
          "s3:ReplicateObject",
          "s3:ReplicateDelete",
          "s3:ReplicateTags"
        ]
        Effect = "Allow"
        Resource = "${aws_s3_bucket.verification_backups.arn}/*"
      }
    ]
  })
}

# Configure replication rules
resource "aws_s3_bucket_replication_configuration" "verification_photos" {
  depends_on = [aws_s3_bucket_versioning.verification_photos]

  role   = aws_iam_role.verification_replication.arn
  bucket = aws_s3_bucket.verification_photos.id

  rule {
    id     = "verification-backup"
    status = "Enabled"

    delete_marker_replication {
      status = "Enabled"
    }

    filter {
      prefix = "processed/"  # Only replicate processed files
    }

    destination {
      bucket        = aws_s3_bucket.verification_backups.arn
      storage_class = "STANDARD_IA"  # Use cheaper storage for backups
    }
  }
}

# IAM role for Rekognition access
# Required for face detection and comparison
resource "aws_iam_role" "rekognition_role" {
  name = "rekognition-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "rekognition.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.common_tags, {
    Name = "rekognition-role-${var.environment}"
    Purpose = "Face Recognition"
  })
}

# IAM policy for Rekognition operations
resource "aws_iam_role_policy" "rekognition_policy" {
  name = "rekognition-policy-${var.environment}"
  role = aws_iam_role.rekognition_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "rekognition:CompareFaces",
          "rekognition:DetectFaces",
          "rekognition:SearchFacesByImage",
          "rekognition:IndexFaces",
          "rekognition:CreateCollection",
          "rekognition:DeleteCollection",
          "rekognition:DescribeCollection",
          "rekognition:ListCollections"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject"
        ]
        Resource = "${aws_s3_bucket.verification_photos.arn}/*"
      }
    ]
  })
}

# Add Rekognition permissions to ECS task role
resource "aws_iam_role_policy_attachment" "ecs_task_rekognition" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonRekognitionFullAccess"
}

# Add S3 permissions to ECS task role
resource "aws_iam_role_policy" "ecs_task_s3_verification" {
  name = "ecs-task-s3-verification-${var.environment}"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.verification_photos.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.verification_photos.arn
      }
    ]
  })
}

# Rest of infrastructure remains unchanged...
