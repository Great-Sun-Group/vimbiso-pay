# ECS Task Definition
resource "aws_ecs_task_definition" "app" {
  family                   = "vimbiso-pay-${var.environment}"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn           = var.task_role_arn

  container_definitions = jsonencode([
    {
      name         = "redis"
      image        = "redis:7-alpine"
      essential    = true
      memory       = floor(var.task_memory * 0.25)
      cpu          = floor(var.task_cpu * 0.25)
      user         = "root"
      portMappings = [
        {
          containerPort = var.redis_port
          hostPort     = var.redis_port
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "LANG", value = "en_US.UTF-8" },
        { name = "LANGUAGE", value = "en_US:en" },
        { name = "LC_ALL", value = "en_US.UTF-8" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "redis"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli ping || exit 1"]
        interval    = 15
        timeout     = 10
        retries     = 5
        startPeriod = 90
      }
      mountPoints = [
        {
          sourceVolume  = "redis-data"
          containerPath = "/redis"
          readOnly     = false
        }
      ]
      ulimits = [
        {
          name = "nofile"
          softLimit = 65536
          hardLimit = 65536
        }
      ]
      systemControls = [
        {
          namespace = "net.core.somaxconn"
          value     = "1024"
        }
      ]
      command = [
        "sh",
        "-c",
        "echo 1 > /proc/sys/vm/overcommit_memory || true && mkdir -p /redis && chown -R root:root /redis && redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --bind 0.0.0.0 --dir /redis --port ${var.redis_port}"
      ]
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.75)
      cpu          = floor(var.task_cpu * 0.75)
      environment  = [
        { name = "DJANGO_ENV", value = var.environment },
        { name = "DJANGO_SECRET", value = var.django_env.django_secret },
        { name = "DEBUG", value = tostring(var.django_env.debug) },
        { name = "ALLOWED_HOSTS", value = "*.amazonaws.com,vimbiso-pay-alb-${var.environment}-427225791.af-south-1.elb.amazonaws.com,${var.environment}.whatsapp.vimbisopay.africa" },
        { name = "MYCREDEX_APP_URL", value = var.django_env.mycredex_app_url },
        { name = "CLIENT_API_KEY", value = var.django_env.client_api_key },
        { name = "WHATSAPP_API_URL", value = var.django_env.whatsapp_api_url },
        { name = "WHATSAPP_ACCESS_TOKEN", value = var.django_env.whatsapp_access_token },
        { name = "WHATSAPP_PHONE_NUMBER_ID", value = var.django_env.whatsapp_phone_number_id },
        { name = "WHATSAPP_BUSINESS_ID", value = var.django_env.whatsapp_business_id },
        { name = "WHATSAPP_REGISTRATION_FLOW_ID", value = var.django_env.whatsapp_registration_flow_id },
        { name = "WHATSAPP_COMPANY_REGISTRATION_FLOW_ID", value = var.django_env.whatsapp_company_registration_flow_id },
        { name = "REDIS_URL", value = "redis://redis:${var.redis_port}/0" },
        { name = "GUNICORN_WORKERS", value = "2" },
        { name = "GUNICORN_TIMEOUT", value = "120" },
        { name = "DJANGO_LOG_LEVEL", value = "DEBUG" },
        { name = "LANG", value = "en_US.UTF-8" },
        { name = "LANGUAGE", value = "en_US:en" },
        { name = "LC_ALL", value = "en_US.UTF-8" }
      ]
      portMappings = [
        {
          containerPort = var.app_port
          hostPort      = var.app_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "app"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          awslogs-multiline-pattern = "^\\[\\d{4}-\\d{2}-\\d{2}"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f http://localhost:${var.app_port}/health/ || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 5
        startPeriod = 120
      }
      mountPoints = [
        {
          sourceVolume  = "app-data"
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
      command = [
        "sh",
        "-c",
        "set -e && mkdir -p /app/data/{db,static,media,logs} && chmod -R 755 /app/data && ./start_app.sh"
      ]
      ulimits = [
        {
          name = "nofile"
          softLimit = 65536
          hardLimit = 65536
        }
      ]
      systemControls = [
        {
          namespace = "net.core.somaxconn"
          value     = "1024"
        }
      ]
    }
  ])

  volume {
    name = "app-data"
    efs_volume_configuration {
      file_system_id = var.efs_file_system_id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.app_access_point_id
        iam = "ENABLED"
      }
      root_directory = "/"
    }
  }

  volume {
    name = "redis-data"
    efs_volume_configuration {
      file_system_id = var.efs_file_system_id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.redis_access_point_id
        iam = "ENABLED"
      }
      root_directory = "/"
    }
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-task-${var.environment}"
  })
}
