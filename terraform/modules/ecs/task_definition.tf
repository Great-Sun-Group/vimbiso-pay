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
      image        = "public.ecr.aws/docker/library/redis:7.0-alpine"
      essential    = true
      memory       = floor(var.task_memory * 0.35)
      cpu          = floor(var.task_cpu * 0.35)
      user         = "redis"
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
          containerPath = "/data"
          readOnly     = false
        }
      ]
      environment = [
        {
          name  = "TZ"
          value = "UTC"
        }
      ]
      command = [
        "sh",
        "-c",
        <<-EOT
        # Create required directories
        mkdir -p /data/appendonlydir || true
        touch /data/appendonly.aof || true

        # Fix any corrupted AOF files
        if [ -f /data/appendonlydir/appendonly.aof.1.incr.aof ]; then
          echo "Checking AOF file integrity..."
          if ! redis-check-aof --fix /data/appendonlydir/appendonly.aof.1.incr.aof; then
            echo "AOF file corrupted, removing and starting fresh..."
            rm -f /data/appendonlydir/appendonly.aof.1.incr.aof
            rm -f /data/appendonlydir/appendonly.aof.manifest
          fi
        fi

        # Start Redis server with persistence settings
        echo "[Redis] Starting server..."
        exec redis-server \
          --appendonly yes \
          --protected-mode no \
          --bind 0.0.0.0 \
          --dir /data \
          --timeout 30 \
          --tcp-keepalive 60 \
          --appendfsync everysec \
          --auto-aof-rewrite-percentage 100 \
          --auto-aof-rewrite-min-size 64mb \
          --aof-load-truncated yes \
          --aof-use-rdb-preamble yes
        EOT
      ]
      healthCheck = {
        command     = ["CMD", "redis-cli", "ping"]
        interval    = 30
        timeout     = 10
        retries     = 3
        startPeriod = 300
      }
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.65)
      cpu          = floor(var.task_cpu * 0.65)
      user         = "root"  # Need root for initial setup
      environment  = [
        { name = "DJANGO_ENV", value = var.environment },
        { name = "DJANGO_SECRET", value = var.django_env.django_secret },
        { name = "DEBUG", value = tostring(var.django_env.debug) },
        { name = "ALLOWED_HOSTS", value = "*" },
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
        { name = "APP_LOG_LEVEL", value = "DEBUG" },
        { name = "REDIS_URL", value = "redis://localhost:${var.redis_port}/0" },
        { name = "LANG", value = "en_US.UTF-8" },
        { name = "LANGUAGE", value = "en_US:en" },
        { name = "LC_ALL", value = "en_US.UTF-8" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "TZ", value = "UTC" },
        { name = "PORT", value = tostring(var.app_port) }
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
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f --max-time 30 http://localhost:${var.app_port}/health/ || exit 1"]
        interval    = 60
        timeout     = 30
        retries     = 3
        startPeriod = 300
      }
      mountPoints = [
        {
          sourceVolume  = "app-data"
          containerPath = "/efs-vols/app-data"
          readOnly     = false
        }
      ]
      command = [
        "bash",
        "-c",
        <<-EOT
        set -ex

        echo "[App] Starting initialization..."

        # Install required packages
        apt-get update
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
          curl \
          iproute2 \
          netcat-traditional \
          dnsutils \
          gosu
        rm -rf /var/lib/apt/lists/*

        # Wait for network readiness
        echo "[App] Waiting for network readiness..."
        until getent hosts localhost >/dev/null 2>&1; do
          echo "[App] Network not ready - sleeping 2s"
          sleep 2
        done

        # Set up directories with proper permissions
        echo "[App] Setting up directories..."
        mkdir -p /efs-vols/app-data/data/{db,static,media,logs}
        chown -R 10001:10001 /efs-vols/app-data
        chmod 777 /efs-vols/app-data/data/db

        echo "[App] Waiting for Redis..."
        until nc -z localhost ${var.redis_port}; do
          echo "[App] Redis is unavailable - sleeping 5s"
          sleep 5
        done

        # Verify Redis is accepting connections
        until redis-cli -h localhost ping >/dev/null 2>&1; do
          echo "[App] Redis not accepting connections - sleeping 5s"
          sleep 5
        done

        # Create symlink for app data directory
        echo "[App] Setting up data directory..."
        ln -sfn /efs-vols/app-data/data /app/data

        cd /app

        echo "[App] Running migrations..."
        python manage.py migrate --noinput

        echo "[App] Collecting static files..."
        python manage.py collectstatic --noinput

        echo "[App] Starting Gunicorn..."
        exec gunicorn config.wsgi:application \
          --bind "0.0.0.0:$${PORT}" \
          --workers "$${GUNICORN_WORKERS:-2}" \
          --worker-class sync \
          --preload \
          --max-requests 1000 \
          --max-requests-jitter 50 \
          --log-level debug \
          --error-logfile - \
          --access-logfile - \
          --capture-output \
          --enable-stdio-inheritance \
          --timeout "$${GUNICORN_TIMEOUT:-120}" \
          --graceful-timeout 30 \
          --keep-alive 65
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
      root_directory = "/"
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
      root_directory = "/"
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
