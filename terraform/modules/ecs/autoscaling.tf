locals {
  service_name = "vimbiso-pay-service-${var.environment}"
}

# Auto Scaling Target
resource "aws_appautoscaling_target" "app" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${aws_ecs_cluster.main.name}/${local.service_name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
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

    scale_in_cooldown  = 300  # 5 minutes to match grace period
    scale_out_cooldown = 60   # Quick scale out for responsiveness
  }
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
    target_value = 80  # Scale at 80% memory utilization

    scale_in_cooldown  = 300  # 5 minutes to match grace period
    scale_out_cooldown = 60   # Quick scale out for responsiveness
  }
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "vimbiso-pay-cpu-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period             = "60"  # Aligned with other intervals
  statistic          = "Average"
  threshold          = var.cpu_threshold
  alarm_description  = "This metric monitors ECS CPU utilization"
  alarm_actions      = [aws_appautoscaling_policy.cpu.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = local.service_name
  }
}

resource "aws_cloudwatch_metric_alarm" "memory_high" {
  alarm_name          = "vimbiso-pay-memory-high-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period             = "60"  # Aligned with other intervals
  statistic          = "Average"
  threshold          = 80    # Align with memory scaling policy
  alarm_description  = "This metric monitors ECS memory utilization"
  alarm_actions      = [aws_appautoscaling_policy.memory.arn]

  dimensions = {
    ClusterName = aws_ecs_cluster.main.name
    ServiceName = local.service_name
  }
}
