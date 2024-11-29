# Network Resources
#---------------------------------------------------------------

# VPC
resource "aws_vpc" "main" {
  cidr_block           = local.current_env.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "vimbiso-pay-vpc-${var.environment}"
  }
}

# Fetch AZs in the current region
data "aws_availability_zones" "available" {}

# Private subnets
resource "aws_subnet" "private" {
  count             = local.current_env.az_count
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index)
  availability_zone = data.aws_availability_zones.available.names[count.index]
  vpc_id            = aws_vpc.main.id

  tags = {
    Name = "vimbiso-pay-private-${var.environment}-${count.index + 1}"
  }
}

# Public subnets
resource "aws_subnet" "public" {
  count                   = local.current_env.az_count
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, local.current_env.az_count + count.index)
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  vpc_id                  = aws_vpc.main.id
  map_public_ip_on_launch = true

  tags = {
    Name = "vimbiso-pay-public-${var.environment}-${count.index + 1}"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "vimbiso-pay-igw-${var.environment}"
  }
}

# Route the public subnet traffic through the IGW
resource "aws_route" "internet_access" {
  route_table_id         = aws_vpc.main.main_route_table_id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.main.id
}

# NAT Gateway with Elastic IPs
resource "aws_eip" "nat" {
  count      = local.current_env.az_count
  vpc        = true
  depends_on = [aws_internet_gateway.main]

  tags = {
    Name = "vimbiso-pay-eip-${var.environment}-${count.index + 1}"
  }
}

resource "aws_nat_gateway" "main" {
  count         = local.current_env.az_count
  subnet_id     = element(aws_subnet.public[*].id, count.index)
  allocation_id = element(aws_eip.nat[*].id, count.index)

  tags = {
    Name = "vimbiso-pay-nat-${var.environment}-${count.index + 1}"
  }
}

# Private route tables
resource "aws_route_table" "private" {
  count  = local.current_env.az_count
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = element(aws_nat_gateway.main[*].id, count.index)
  }

  tags = {
    Name = "vimbiso-pay-private-route-${var.environment}-${count.index + 1}"
  }
}

resource "aws_route_table_association" "private" {
  count          = local.current_env.az_count
  subnet_id      = element(aws_subnet.private[*].id, count.index)
  route_table_id = element(aws_route_table.private[*].id, count.index)
}

#---------------------------------------------------------------
# Security Groups
#---------------------------------------------------------------

resource "aws_security_group" "alb" {
  name        = "vimbiso-pay-alb-${var.environment}"
  description = "Controls access to the ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "ecs_tasks" {
  name        = "vimbiso-pay-ecs-tasks-${var.environment}"
  description = "Allow inbound access from the ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    protocol    = "tcp"
    from_port   = 6379
    to_port     = 6379
    self        = true
    description = "Allow Redis traffic between tasks"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }
}

#---------------------------------------------------------------
# Load Balancer & DNS
#---------------------------------------------------------------

# ACM Certificate
resource "aws_acm_certificate" "main" {
  domain_name       = "${local.current_domain.environment_subdomains[var.environment]}.${local.current_domain.dev_domain_base}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# Route53 Configuration
data "aws_route53_zone" "domain" {
  name = local.current_domain.dev_domain_base
  private_zone = false
}

# Create A record for the domain
resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.domain.zone_id
  name    = "${local.current_domain.environment_subdomains[var.environment]}.${local.current_domain.dev_domain_base}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# DNS Validation record
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
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

resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "vimbiso-pay-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets           = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "app" {
  name        = "vimbiso-pay-tg-${var.environment}"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health/"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }

  # Increased deregistration delay to ensure in-flight requests complete
  deregistration_delay = 60

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate_validation.main.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}

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

#---------------------------------------------------------------
# Container Registry & IAM
#---------------------------------------------------------------

# ECR Repository
resource "aws_ecr_repository" "app" {
  name = "vimbiso-pay-${var.environment}"

  image_scanning_configuration {
    scan_on_push = true
  }
}

# IAM Roles
resource "aws_iam_role" "ecs_execution_role" {
  name = "vimbiso-pay-ecs-execution-${var.environment}"

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
}

resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "ecs_task_role" {
  name = "vimbiso-pay-ecs-task-${var.environment}"

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
}

#---------------------------------------------------------------
# ECS Resources
#---------------------------------------------------------------

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/vimbiso-pay-${var.environment}"
  retention_in_days = 30
}

# Add a time delay after cluster creation
resource "time_sleep" "wait_for_cluster" {
  depends_on = [aws_ecs_cluster.main]
  create_duration = "30s"
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "vimbiso-pay-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-cluster-${var.environment}"
  })
}

# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "vimbiso-pay-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = local.current_env.ecs_task.cpu
  memory                   = local.current_env.ecs_task.memory
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn           = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name         = "redis"
      image        = "redis:7-alpine"
      essential    = true
      memory       = floor(local.current_env.ecs_task.memory * 0.25)
      cpu          = floor(local.current_env.ecs_task.cpu * 0.25)
      portMappings = [
        {
          containerPort = 6379
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = local.current_env.aws_region
          awslogs-stream-prefix = "redis"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
        }
      }
      healthCheck = {
        command     = ["CMD", "redis-cli", "ping"]
        interval    = 30
        timeout     = 5
        retries     = 5
        startPeriod = 60
      }
      mountPoints = [
        {
          sourceVolume  = "data"
          containerPath = "/data"
          readOnly     = false
        }
      ]
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(local.current_env.ecs_task.memory * 0.75)
      cpu          = floor(local.current_env.ecs_task.cpu * 0.75)
      environment  = [
        { name = "DJANGO_ENV", value = var.environment },
        { name = "DJANGO_SECRET", value = var.django_secret },
        { name = "DEBUG", value = tostring(var.debug) },
        { name = "ALLOWED_HOSTS", value = "*.amazonaws.com,${aws_lb.main.dns_name},${local.current_domain.environment_subdomains[var.environment]}.${local.current_domain.dev_domain_base}" },
        { name = "MYCREDEX_APP_URL", value = var.mycredex_app_url },
        { name = "CLIENT_API_KEY", value = var.client_api_key },
        { name = "WHATSAPP_API_URL", value = var.whatsapp_api_url },
        { name = "WHATSAPP_ACCESS_TOKEN", value = var.whatsapp_access_token },
        { name = "WHATSAPP_PHONE_NUMBER_ID", value = var.whatsapp_phone_number_id },
        { name = "WHATSAPP_BUSINESS_ID", value = var.whatsapp_business_id },
        { name = "WHATSAPP_REGISTRATION_FLOW_ID", value = var.whatsapp_registration_flow_id },
        { name = "WHATSAPP_COMPANY_REGISTRATION_FLOW_ID", value = var.whatsapp_company_registration_flow_id },
        { name = "REDIS_URL", value = "redis://localhost:6379/0" }
      ]
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = local.current_env.aws_region
          awslogs-stream-prefix = "app"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:8000/health/ || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 5
        startPeriod = 180
      }
      mountPoints = [
        {
          sourceVolume  = "data"
          containerPath = "/app/data"
          readOnly     = false
        }
      ]
      dependsOn = [
        {
          containerName = "redis"
          condition     = "HEALTHY"
        }
      ]
      user = "root"  # Temporarily run as root to fix permissions
    }
  ])

  volume {
    name = "data"
    efs_volume_configuration {
      file_system_id = aws_efs_file_system.app_data.id
      root_directory = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.app_data.id
        iam = "ENABLED"
      }
    }
  }

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-${var.environment}"
  })
}

# EFS File System
resource "aws_efs_file_system" "app_data" {
  creation_token = "vimbiso-pay-efs-${var.environment}"
  encrypted      = true

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-efs-${var.environment}"
  })
}

# EFS Access Point
resource "aws_efs_access_point" "app_data" {
  file_system_id = aws_efs_file_system.app_data.id

  posix_user {
    gid = 0
    uid = 0
  }

  root_directory {
    path = "/data"
    creation_info {
      owner_gid   = 0
      owner_uid   = 0
      permissions = "755"
    }
  }

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-efs-ap-${var.environment}"
  })
}

# EFS Mount Targets
resource "aws_efs_mount_target" "app_data" {
  count           = length(aws_subnet.private)
  file_system_id  = aws_efs_file_system.app_data.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs.id]
}

# Security Group for EFS
resource "aws_security_group" "efs" {
  name        = "vimbiso-pay-efs-${var.environment}"
  description = "Allow inbound NFS traffic from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from ECS tasks"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-efs-${var.environment}"
  })
}

# ECS Service
resource "aws_ecs_service" "app" {
  name                               = "vimbiso-pay-service-${var.environment}"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = 2
  deployment_minimum_healthy_percent = 50
  deployment_maximum_percent        = 200
  launch_type                       = "FARGATE"
  scheduling_strategy               = "REPLICA"
  platform_version                  = "LATEST"
  wait_for_steady_state            = true

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  deployment_controller {
    type = "ECS"
  }

  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets         = aws_subnet.private[*].id
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.app.arn
    container_name   = "vimbiso-pay-${var.environment}"
    container_port   = 8000
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_ecs_cluster.main, aws_lb_listener.https, aws_efs_mount_target.app_data]

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-service-${var.environment}"
  })
}

# Auto Scaling
resource "aws_appautoscaling_target" "app" {
  max_capacity       = local.current_env.autoscaling.max_capacity
  min_capacity       = local.current_env.autoscaling.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.app]

  tags = merge(local.common_tags, {
    Name = "vimbiso-pay-autoscaling-target-${var.environment}"
  })
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "vimbiso-pay-cpu-autoscaling-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = local.current_env.autoscaling.cpu_threshold
  }

  depends_on = [aws_appautoscaling_target.app]
}

resource "aws_appautoscaling_policy" "memory" {
  name               = "vimbiso-pay-memory-autoscaling-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageMemoryUtilization"
    }
    target_value = local.current_env.autoscaling.memory_threshold
  }

  depends_on = [aws_appautoscaling_target.app]
}
