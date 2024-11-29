# ECS Service
resource "aws_ecs_service" "app" {
  name                               = "vimbiso-pay-service-${var.environment}"
  cluster                           = aws_ecs_cluster.main.id
  task_definition                   = aws_ecs_task_definition.app.arn
  desired_count                     = var.min_capacity
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent        = 200
  launch_type                       = "FARGATE"
  scheduling_strategy               = "REPLICA"
  platform_version                  = "LATEST"
  wait_for_steady_state            = true

  # Enable deployment circuit breaker with rollback
  deployment_circuit_breaker {
    enable   = true
    rollback = true
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

  # Capacity provider strategy
  capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight           = 100
    base             = 1
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes       = [desired_count, task_definition]
  }

  # Service registry configuration (if using service discovery)
  service_registries {
    registry_arn = aws_service_discovery_service.app.arn
  }

  depends_on = [
    aws_service_discovery_service.app,
    time_sleep.wait_for_cluster
  ]

  tags = merge(var.tags, {
    Name = "vimbiso-pay-service-${var.environment}"
  })
}

# Service Discovery Private DNS Namespace
resource "aws_service_discovery_private_dns_namespace" "app" {
  name        = "vimbiso-pay-${var.environment}.local"
  description = "Service Discovery namespace for VimbisoPay ${var.environment}"
  vpc         = var.vpc_id

  tags = merge(var.tags, {
    Name = "vimbiso-pay-dns-${var.environment}"
  })
}

# Service Discovery Service
resource "aws_service_discovery_service" "app" {
  name = "vimbiso-pay-${var.environment}"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.app.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-discovery-${var.environment}"
  })
}
