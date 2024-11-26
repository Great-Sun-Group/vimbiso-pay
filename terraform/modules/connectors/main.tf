# Add us-east-1 provider for ACM certificates
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# Local variables
locals {
  common_tags = {
    Environment = var.environment
    Project     = "Vimbiso Pay"
    ManagedBy   = "Terraform"
  }
  
  # Domain logic with validation
  is_production = var.environment == "production"
  
  # Domain logic
  domain = local.is_production ? var.production_domain : "${var.environment_subdomains[var.environment]}.${var.dev_domain_base}"
  domain_base = local.is_production ? var.production_domain : var.dev_domain_base
}

# VPC
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-vpc-${var.environment}"
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

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-private-subnet-${var.environment}-${count.index + 1}"
  })
}

# Create public subnets, each in a different AZ
resource "aws_subnet" "public" {
  count                   = var.az_count
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, var.az_count + count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  vpc_id                  = aws_vpc.main.id
  map_public_ip_on_launch = true

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-public-subnet-${var.environment}-${count.index + 1}"
  })
}

# Internet Gateway for the public subnet
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-igw-${var.environment}"
  })
}

# Route the public subnet traffic through the IGW
resource "aws_route" "internet_access" {
  route_table_id         = aws_vpc.main.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# Create a NAT gateway with an Elastic IP for each private subnet
resource "aws_eip" "nat" {
  count      = var.az_count
  vpc        = true
  depends_on = [aws_internet_gateway.main]

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-eip-${var.environment}-${count.index + 1}"
  })
}

resource "aws_nat_gateway" "main" {
  count         = var.az_count
  subnet_id     = element(aws_subnet.public[*].id, count.index)
  allocation_id = element(aws_eip.nat[*].id, count.index)

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-nat-${var.environment}-${count.index + 1}"
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

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-private-route-table-${var.environment}-${count.index + 1}"
  })
}

# Associate the private subnets with the appropriate route tables
resource "aws_route_table_association" "private" {
  count          = var.az_count
  subnet_id      = element(aws_subnet.private[*].id, count.index)
  route_table_id = element(aws_route_table.private[*].id, count.index)
}

# ALB security group
resource "aws_security_group" "alb" {
  name        = "vimbiso-pay-alb-sg-${var.environment}"
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

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-alb-sg-${var.environment}"
  })
}

# ECS tasks security group
resource "aws_security_group" "ecs_tasks" {
  name        = "vimbiso-pay-ecs-tasks-sg-${var.environment}"
  description = "Allow inbound access from the ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.alb.id]
    description     = "Allow inbound traffic from ALB"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-ecs-tasks-sg-${var.environment}"
  })
}

# ACM Certificate for ALB
resource "aws_acm_certificate" "cert" {
  domain_name               = local.domain
  validation_method         = "DNS"

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-cert-${var.environment}"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Get the hosted zone for the domain
data "aws_route53_zone" "domain" {
  name = local.domain_base
}

# Create DNS records for certificate validation
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.cert.domain_validation_options : dvo.domain_name => {
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

# Certificate validation
resource "aws_acm_certificate_validation" "cert" {
  certificate_arn         = aws_acm_certificate.cert.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# Application Load Balancer (ALB)
resource "aws_lb" "main" {
  name               = "vimbiso-pay-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  tags = local.common_tags
}

# Target Group
resource "aws_lb_target_group" "app" {
  name        = "vimbiso-pay-tg-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    healthy_threshold   = "2"
    interval            = "30"
    protocol            = "HTTP"
    matcher             = "200"
    timeout             = "10"
    path                = "/health/"
    unhealthy_threshold = "3"
  }

  tags = local.common_tags
}

# Create Route53 record
resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.domain.zone_id
  name    = local.domain
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# ALB Listener
resource "aws_lb_listener" "app" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate_validation.cert.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

# HTTP to HTTPS redirect
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"

    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# ECR Repository
resource "aws_ecr_repository" "app" {
  name = "vimbiso-pay-${var.environment}"
  
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-ecr-${var.environment}"
  })
}

# ECS execution role
resource "aws_iam_role" "ecs_execution_role" {
  name = "vimbiso-pay-ecs-execution-role-${var.environment}"

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

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-ecs-execution-role-${var.environment}"
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS task role
resource "aws_iam_role" "ecs_task_role" {
  name = "vimbiso-pay-ecs-task-role-${var.environment}"

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

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-ecs-task-role-${var.environment}"
  })
}

# Add CloudWatch Logs permissions to ECS task role
resource "aws_iam_role_policy" "ecs_task_role_policy" {
  name = "vimbiso-pay-ecs-task-role-policy-${var.environment}"
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

# CloudWatch log group
resource "aws_cloudwatch_log_group" "ecs_logs" {
  name              = "/ecs/vimbiso-pay-${var.environment}"
  retention_in_days = 30

  tags = merge(local.common_tags, {
    Name = "/ecs/vimbiso-pay-${var.environment}"
  })
}
