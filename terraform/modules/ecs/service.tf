# ECS Service
resource "aws_ecs_service" "app" {
  name                               = "vimbiso-pay-service-${var.environment}"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.min_capacity
  deployment_minimum_healthy_percent = 100  # Keep at least one task running
  deployment_maximum_percent        = 200
  scheduling_strategy               = "REPLICA"
  force_new_deployment             = true
  health_check_grace_period_seconds = 300  # 5 minutes for startup

  # Keep rollback disabled for debugging
  deployment_circuit_breaker {
    enable   = true
    rollback = false  # Disabled to preserve logs and debug info
  }

  deployment_controller {
    type = "ECS"
  }

  network_configuration {
    security_groups  = [var.ecs_tasks_security_group_id]
    subnets         = var.private_subnet_ids
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "vimbiso-pay-${var.environment}"
    container_port   = var.app_port
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 100
    base             = 1
  }

  service_registries {
    registry_arn = aws_service_discovery_service.redis.arn
    container_name = "redis"
  }

  # Only ignore changes to desired_count and capacity strategy
  lifecycle {
    ignore_changes = [
      desired_count,
      capacity_provider_strategy
    ]
  }

  depends_on = [
    aws_service_discovery_service.app,
    aws_service_discovery_service.redis,
    aws_ecs_cluster.main,
    var.efs_mount_targets  # Ensure EFS mount targets are ready
  ]

  tags = merge(var.tags, {
    Name = "vimbiso-pay-service-${var.environment}"
  })
}
