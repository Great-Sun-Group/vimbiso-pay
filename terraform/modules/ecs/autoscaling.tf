# Auto Scaling Target
resource "aws_appautoscaling_target" "app" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.app.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"

  depends_on = [aws_ecs_service.app]

  tags = merge(var.tags, {
    Name = "vimbiso-pay-autoscaling-target-${var.environment}"
  })
}

# CPU Scaling Policy
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
    target_value = var.cpu_threshold

    # Longer cooldowns to prevent interference during deployments
    scale_in_cooldown  = 900  # 15 minutes to match health check grace period
    scale_out_cooldown = 300  # 5 minutes to allow proper initialization
    disable_scale_in   = true # Prevent scale-in during deployments
  }

  depends_on = [aws_appautoscaling_target.app]
}

# Memory Scaling Policy
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
    target_value = var.memory_threshold

    # Match CPU policy cooldowns for consistency
    scale_in_cooldown  = 900  # 15 minutes to match health check grace period
    scale_out_cooldown = 300  # 5 minutes to allow proper initialization
    disable_scale_in   = true # Prevent scale-in during deployments
  }

  depends_on = [aws_appautoscaling_target.app]
}

# Wait for ECS service to be stable
resource "time_sleep" "wait_for_service_stable" {
  depends_on = [aws_ecs_service.app]

  create_duration = "30s"
}

# Request Count Scaling Policy
resource "aws_appautoscaling_policy" "requests" {
  name               = "vimbiso-pay-requests-autoscaling-${var.environment}"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.app.resource_id
  scalable_dimension = aws_appautoscaling_target.app.scalable_dimension
  service_namespace  = aws_appautoscaling_target.app.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label        = "${data.aws_lb.app.arn_suffix}/${data.aws_lb_target_group.app.arn_suffix}"
    }
    target_value = 1000  # Target requests per target

    # Match other policy cooldowns
    scale_in_cooldown  = 900  # 15 minutes to match health check grace period
    scale_out_cooldown = 300  # 5 minutes to allow proper initialization
    disable_scale_in   = true # Prevent scale-in during deployments
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_appautoscaling_target.app,
    time_sleep.wait_for_service_stable,
    aws_ecs_service.app
  ]
}

# Data sources for ALB and target group ARN suffixes
data "aws_lb" "app" {
  arn = var.alb_arn
}

data "aws_lb_target_group" "app" {
  arn = var.target_group_arn
}

# CloudWatch Alarms for Auto Scaling
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "vimbiso-pay-cpu-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "CPUUtilization"
  namespace          = "AWS/ECS"
  period             = "60"
  statistic          = "Average"
  threshold          = var.cpu_threshold
  alarm_description  = "This metric monitors ECS CPU utilization"
  alarm_actions      = [aws_appautoscaling_policy.cpu.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-cpu-alarm-${var.environment}"
  })
}

resource "aws_cloudwatch_metric_alarm" "memory_high" {
  alarm_name          = "vimbiso-pay-memory-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name        = "MemoryUtilization"
  namespace          = "AWS/ECS"
  period             = "60"
  statistic          = "Average"
  threshold          = var.memory_threshold
  alarm_description  = "This metric monitors ECS memory utilization"
  alarm_actions      = [aws_appautoscaling_policy.memory.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = aws_ecs_service.app.name
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-memory-alarm-${var.environment}"
  })
}
