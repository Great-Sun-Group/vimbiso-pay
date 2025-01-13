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
      name         = "redis-state"
      image        = "public.ecr.aws/docker/library/redis:7.0-alpine"
      essential    = true
      memory       = floor(var.task_memory * 0.3)  # Increased memory allocation
      cpu          = floor(var.task_cpu * 0.3)     # Increased CPU allocation
      user         = "root"  # Need root for initial setup
      portMappings = [
        {
          containerPort = var.redis_state_port
          hostPort     = var.redis_state_port
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.app.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "redis-state"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      mountPoints = [
        {
          sourceVolume  = "redis-state-data"
          containerPath = "/redis/state"
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
        echo "[Redis] Starting initialization..."

        # Basic setup
        echo "[Redis] Setting up data directory..."
        # Use su-exec instead of gosu (built into Alpine)
        apk add --no-cache su-exec

        # Create redis user/group only if they don't exist
        if ! getent group redis >/dev/null; then
          addgroup -S -g 999 redis
        fi
        if ! getent passwd redis >/dev/null; then
          adduser -S -u 999 -G redis redis
        fi

        # Ensure redis user owns the state directory
        install -d -m 0755 -o redis -g redis /redis/state

        # Log Redis environment
        echo "[Redis] Environment:"
        echo "  User: $(id redis)"
        echo "  Mount status: $(mountpoint -v /redis/state)"
        echo "  Mount details: $(df -h /redis/state)"
        echo "  Directory contents: $(ls -la /redis/state)"
        echo "  Port: ${var.redis_state_port}"

        echo "[Redis] Starting Redis server with optimized settings..."
        exec su-exec redis redis-server \
          --appendonly yes \
          --appendfsync no \
          --no-appendfsync-on-rewrite yes \
          --aof-rewrite-incremental-fsync yes \
          --auto-aof-rewrite-percentage 100 \
          --auto-aof-rewrite-min-size 128mb \
          --aof-load-truncated yes \
          --aof-use-rdb-preamble yes \
          --protected-mode no \
          --bind 0.0.0.0 \
          --port ${var.redis_state_port} \
          --dir /redis/state \
          --timeout 60 \
          --tcp-keepalive 300 \
          --maxmemory-policy allkeys-lru \
          --maxmemory ${floor(var.task_memory * 0.3 * 0.90)}mb \
          --save "" \
          --stop-writes-on-bgsave-error no \
          --ignore-warnings ARM64-COW-BUG \
          --activedefrag no \
          --logfile "" \
          --daemonize no
        EOT
      ]
      healthCheck = {
        command     = ["CMD-SHELL", "redis-cli -p ${var.redis_state_port} ping || exit 1"]
        interval    = 45     # Longer interval to allow more time between checks
        timeout     = 15     # Increased timeout for EFS operations
        retries     = 10     # Maximum allowed by AWS ECS
        startPeriod = 300    # Maximum allowed by AWS ECS
      }
    },
    {
      name         = "vimbiso-pay-${var.environment}"
      image        = var.docker_image
      essential    = true
      memory       = floor(var.task_memory * 0.6)
      cpu          = floor(var.task_cpu * 0.6)
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
        { name = "REDIS_URL", value = "redis://localhost:${var.redis_state_port}/0" },
        { name = "LANG", value = "en_US.UTF-8" },
        { name = "LANGUAGE", value = "en_US:en" },
        { name = "LC_ALL", value = "en_US.UTF-8" },
        { name = "AWS_REGION", value = var.aws_region },
        { name = "TZ", value = "UTC" },
        { name = "PORT", value = "8000" }
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
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "vimbiso-pay-${var.environment}"
          awslogs-datetime-format = "%Y-%m-%d %H:%M:%S"
          awslogs-create-group  = "true"
          mode                  = "non-blocking"
          max-buffer-size       = "4m"
        }
      }
      healthCheck = {
        command     = ["CMD-SHELL", "curl -f --max-time 10 --retry 3 --retry-delay 5 --retry-max-time 45 http://127.0.0.1:8000/health/ || exit 1"]
        interval    = 30
        timeout     = 10
        retries     = 5
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

        # Small delay to ensure log infrastructure is ready
        sleep 2

        echo "[App] Starting initialization..."
        echo "[App] Container environment: ${var.environment}"

        echo "[App] Installing required packages..."
        apt-get update 2>&1
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends 2>&1 \
          curl \
          iproute2 \
          netcat-traditional \
          dnsutils \
          gosu \
          redis-tools
        rm -rf /var/lib/apt/lists/* 2>&1
        echo "[App] Package installation complete"

        echo "[App] Checking network readiness..."
        until getent hosts localhost >/dev/null 2>&1; do
          echo "[App] Network not ready - sleeping 2s"
          sleep 2
        done

        echo "[App] Checking EFS mount point..."
        if ! mountpoint -q /efs-vols/app-data; then
          echo "[App] Error: /efs-vols/app-data is not a mount point"
          exit 1
        fi
        echo "[App] EFS mount point verified"

        echo "[App] Creating and configuring data directories..."
        mkdir -p /efs-vols/app-data/data/{db,static,media,logs} 2>&1 || { echo "[App] Failed to create data directories"; exit 1; }
        chown -R 10001:10001 /efs-vols/app-data 2>&1 || { echo "[App] Failed to set directory ownership"; exit 1; }
        chmod 777 /efs-vols/app-data/data/db 2>&1 || { echo "[App] Failed to set directory permissions"; exit 1; }
        echo "[App] Data directories configured successfully"

        echo "[App] Waiting for Redis State..."
        until nc -z localhost ${var.redis_state_port}; do
          echo "[App] Redis State port not available - sleeping 5s"
          sleep 5
        done

        # Test Redis connectivity with detailed output
        echo "[App] Testing Redis connectivity..."
        max_attempts=30
        attempt=1
        while [ $attempt -le $max_attempts ]; do
          echo "[App] Redis connection attempt $attempt/$max_attempts"
          if redis-cli -p ${var.redis_state_port} ping > /dev/null 2>&1; then
            echo "[App] Redis State INFO:"
            redis-cli -p ${var.redis_state_port} info | grep -E "^(# Server|redis_version|connected_clients|used_memory|used_memory_human|used_memory_peak|used_memory_peak_human|role)"
            break
          else
            echo "[App] Redis PING failed"
            if [ $attempt -eq $max_attempts ]; then
              echo "[App] Redis connection attempts exhausted"
              exit 1
            fi
          fi

          attempt=$((attempt + 1))
          sleep 5
        done

        # Verify Redis is accepting connections before proceeding
        if ! redis-cli -p ${var.redis_state_port} ping > /dev/null 2>&1; then
          echo "[App] Final Redis connectivity check failed"
          exit 1
        fi

        # Test Django Redis connections
        echo "[App] Testing Django Redis connections..."
        cd /app
        python << EOF
import redis
from django.conf import settings
import sys

print("[App] Attempting to connect to Redis State using settings.REDIS_URL:", settings.REDIS_URL)
try:
    rs = redis.from_url(settings.REDIS_URL)
    rs.ping()
    print("[App] Django Redis connection successful")
except Exception as e:
    print("[App] Django Redis connections failed:", str(e))
    sys.exit(1)
EOF

        echo "[App] Creating data symlink..."
        ln -sfn /efs-vols/app-data/data /app/data

        echo "[App] Running database migrations..."
        python manage.py migrate --noinput 2>&1

        echo "[App] Collecting static files..."
        python manage.py collectstatic --noinput 2>&1

        echo "[App] Starting Gunicorn..."
        exec gunicorn config.wsgi:application \
          --bind "0.0.0.0:8000" \
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
          --keep-alive 65 \
          --forwarded-allow-ips "*" \
          --access-logformat '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" "%({X-Forwarded-For}i)s" "%({X-Forwarded-Proto}i)s"'
        EOT
      ]
      dependsOn = [
        {
          containerName = "redis-state"
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
    name = "redis-state-data"
    efs_volume_configuration {
      file_system_id = var.efs_file_system_id
      root_directory = "/"
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = var.redis_state_access_point_id
        iam = "ENABLED"
      }
    }
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-task-${var.environment}"
  })
}
