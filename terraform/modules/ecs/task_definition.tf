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
      memory       = floor(var.task_memory * 0.35)  # Increased to 35%
      cpu          = floor(var.task_cpu * 0.35)     # Increased to 35%
      user         = "redis:redis"
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
        command     = ["CMD-SHELL", "redis-cli -h localhost ping || exit 1"]
        interval    = 5         # More frequent checks
        timeout     = 3         # Shorter timeout
        retries     = 3
        startPeriod = 10        # Shorter start period
      }
      mountPoints = [
        {
          sourceVolume  = "redis-data"
          containerPath = "/data"
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
        <<-EOT
        set -e

        # Wait for EFS mount to be ready
        until mountpoint -q /data; do
          echo "Waiting for EFS mount..."
          sleep 2
        done

        # Verify directory permissions
        mkdir -p /data
        chown redis:redis /data
        chmod 755 /data

        # Create Redis config with optimized settings
        cat > /tmp/redis.conf << EOF
        # Memory settings
        maxmemory 512mb
        maxmemory-policy allkeys-lru
        maxmemory-samples 10

        # Initial persistence settings (AOF disabled on startup)
        appendonly no
        appendfsync everysec
        no-appendfsync-on-rewrite yes
        auto-aof-rewrite-percentage 100
        auto-aof-rewrite-min-size 64mb

        # Performance settings
        bind 0.0.0.0
        dir /data
        port ${var.redis_port}
        activerehashing yes
        lazyfree-lazy-eviction yes
        lazyfree-lazy-expire yes
        lazyfree-lazy-server-del yes
        replica-lazy-flush yes
        dynamic-hz yes

        # Connection settings
        timeout 0
        tcp-keepalive 60

        # Ignore warnings that don't affect functionality
        ignore-warnings ARM64-COW-BUG
        EOF

        # Start Redis without AOF initially
        redis-server /tmp/redis.conf &
        REDIS_PID=$!

        # Wait for Redis to be ready
        until redis-cli ping; do
          echo "Waiting for Redis to be ready..."
          sleep 1
        done

        # Enable AOF after Redis is running
        echo "Enabling AOF persistence..."
        redis-cli config set appendonly yes

        # Wait for Redis process
        wait $REDIS_PID
        EOT
      ]
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.65)  # Adjusted to complement Redis
      cpu          = floor(var.task_cpu * 0.65)     # Adjusted to complement Redis
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
