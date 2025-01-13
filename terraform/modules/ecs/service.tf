# ECS Service
resource "aws_ecs_service" "app" {
  name                               = "vimbiso-pay-service-${var.environment}"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.min_capacity
  deployment_minimum_healthy_percent = 50   # Keep at least half of tasks running during deployment
  deployment_maximum_percent        = 200  # Allow double capacity during deployment
  scheduling_strategy               = "REPLICA"
  force_new_deployment             = false  # Let ECS control deployments
  health_check_grace_period_seconds = 900   # 15 minutes for complete startup
  enable_execute_command           = true   # Allow debugging if needed

  # Circuit breaker configuration
  # NOTE: During normal operation, rollback should be enabled (rollback = true).
  # However, when debugging deployment issues, setting rollback = false helps preserve
  # the failed state for investigation. Remember to re-enable rollback after debugging.
  deployment_circuit_breaker {
    enable   = true
    rollback = false  # Temporarily disabled for debugging deployment issues
  }

  deployment_controller {
    type = "ECS"
  }

  network_configuration {
    security_groups  = [var.ecs_tasks_security_group_id]
    subnets         = var.private_subnet_ids
    assign_public_ip = false  # Tasks in private subnets
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "vimbiso-pay-${var.environment}"
    container_port   = var.app_port
  }

  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 100
    base             = 0  # Remove forced base capacity to allow proper scaling
  }

  # Ignore changes to desired_count since it's managed by autoscaling
  # But track other changes to ensure proper deployments
  lifecycle {
    ignore_changes = [
      desired_count,
      capacity_provider_strategy
    ]
  }

  depends_on = [
    aws_ecs_cluster.main,
    var.efs_mount_targets  # Ensure EFS mount targets are ready
  ]

  tags = merge(var.tags, {
    Name = "vimbiso-pay-service-${var.environment}"
  })
}
