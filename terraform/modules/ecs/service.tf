# ECS Service
resource "aws_ecs_service" "app" {
  name                               = local.service_name
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.min_capacity
  deployment_minimum_healthy_percent = 0    # Allow all old tasks to be stopped since we don't need state transfer
  deployment_maximum_percent        = 100  # No need for extra capacity since we start fresh
  scheduling_strategy               = "REPLICA"
  force_new_deployment             = false
  health_check_grace_period_seconds = 60    # Reduced to 1 minute since Redis starts fresh
  enable_execute_command           = true

  deployment_circuit_breaker {
    enable   = true
    rollback = false  # Auto-rollback for failed deployments
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
    base             = 0
  }

  lifecycle {
    ignore_changes = [
      desired_count,
      capacity_provider_strategy
    ]
    create_before_destroy = true
  }

  depends_on = [
    aws_ecs_cluster.main,
    var.efs_mount_targets
  ]
}
