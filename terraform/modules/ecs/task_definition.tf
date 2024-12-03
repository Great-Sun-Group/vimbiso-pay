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
      image        = "public.ecr.aws/docker/library/redis:7-alpine"
      essential    = true
      memory       = floor(var.task_memory * 0.35)
      cpu          = floor(var.task_cpu * 0.35)
      user         = "999:999"  # Alpine Redis user/group
      portMappings = [
        {
          containerPort = var.redis_port
          hostPort     = var.redis_port
          protocol      = "tcp"
        }
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
      mountPoints = [
        {
          sourceVolume  = "redis-data"
          containerPath = "/efs-vols/redis-data"
          readOnly     = false
        }
      ]
      environment = [
        {
          name  = "TZ",
          value = "UTC"
        }
      ]
      command = [
        "sh",
        "-c",
        <<-EOT
        mkdir -p /efs-vols/redis-data
        chown -R redis:redis /efs-vols/redis-data
        echo "[Redis] Starting Redis server..."
        redis-server --appendonly yes --protected-mode no --bind 0.0.0.0 --dir /efs-vols/redis-data
        EOT
      ]
      healthCheck = {
        command     = ["CMD", "redis-cli", "ping"]
        interval    = 10
        timeout     = 5
        retries     = 3
        startPeriod = 10
      }
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.65)
      cpu          = floor(var.task_cpu * 0.65)
      environment  = [
        { name = "DJANGO_ENV", value = var.environment },
        { name = "DJANGO_SECRET", value = var.django_env.django_secret },
        { name = "DEBUG", value = tostring(var.django_env.debug) },
        { name = "ALLOWED_HOSTS", value = var.allowed_hosts },
        { name = "MYCREDEX_APP_URL", value = var.django_env.mycredex_app_url },
        { name = "CLIENT_API_KEY", value = var.django_env.client_api_key },
        { name = "WHATSAPP_API_URL", value = var.django_env.whatsapp_api_url },
        { name = "WHATSAPP_ACCESS_TOKEN", value = var.django_env.whatsapp_access_token },
        { name = "WHATSAPP_PHONE_NUMBER_ID", value = var.django_env.whatsapp_phone_number_id },
        { name = "WHATSAPP_BUSINESS_ID", value = var.django_env.whatsapp_business_id },
        { name = "WHATSAPP_REGISTRATION_FLOW_ID", value = var.django_env.whatsapp_registration_flow_id },
        { name = "WHATSAPP_COMPANY_REGISTRATION_FLOW_ID", value = var.django_env.whatsapp_company_registration_flow_id },
        { name = "GUNICORN_WORKERS", value = "2" },
        { name = "GUNICORN_TIMEOUT", value = "120" },
        { name = "DJANGO_LOG_LEVEL", value = "DEBUG" },
        { name = "REDIS_URL", value = "redis://localhost:${var.redis_port}/0" },
        { name = "LANG", value = "en_US.UTF-8" },
        { name = "LANGUAGE", value = "en_US:en" },
        { name = "LC_ALL", value = "en_US.UTF-8" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "TZ", value = "UTC" }
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
        retries     = 3
        startPeriod = 120
      }
      mountPoints = [
        {
          sourceVolume  = "app-data"
          containerPath = "/efs-vols/app-data"
          readOnly     = false
        }
      ]
      command = [
        "sh",
        "-c",
        <<-EOT
        echo "[App] Waiting for Redis..."
        timeout=60
        until redis-cli -h localhost ping > /dev/null 2>&1; do
          timeout=$((timeout - 1))
          if [ $timeout -le 0 ]; then
            echo "[App] ERROR: Redis not ready after 60 seconds"
            exit 1
          fi
          sleep 1
        done
        echo "[App] Redis is ready"

        exec ./start_app.sh
        EOT
      ]
      dependsOn = [
        {
          containerName = "redis"
          condition     = "HEALTHY"
        }
      ]
    }
  ])

  volume {
    name = "app-data"
    efs_volume_configuration {
      file_system_id = var.efs_file_system_id
      root_directory = "/efs-vols/app-data"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.app_access_point_id
        iam = "ENABLED"
      }
    }
  }

  volume {
    name = "redis-data"
    efs_volume_configuration {
      file_system_id = var.efs_file_system_id
      root_directory = "/efs-vols/redis-data"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.redis_access_point_id
        iam = "ENABLED"
      }
    }
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-task-${var.environment}"
  })
}
