# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/vimbiso-pay-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = merge(var.tags, {
    Name = "vimbiso-pay-logs-${var.environment}"
  })
}

# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "vimbiso-pay-cluster-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.app.name
      }
    }
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-cluster-${var.environment}"
  })
}

# Add CloudWatch log metric filters for error monitoring
resource "aws_cloudwatch_log_metric_filter" "error_logs" {
  name           = "vimbiso-pay-errors-${var.environment}"
  pattern        = "[timestamp, level=ERROR, message]"
  log_group_name = aws_cloudwatch_log_group.app.name

  metric_transformation {
    name          = "ErrorCount"
    namespace     = "VimbisoPay/${var.environment}"
    value         = "1"
    default_value = "0"
  }
}

# CloudWatch Alarm for Error Logs
resource "aws_cloudwatch_metric_alarm" "error_logs" {
  alarm_name          = "vimbiso-pay-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name        = "ErrorCount"
  namespace          = "VimbisoPay/${var.environment}"
  period             = "300"
  statistic          = "Sum"
  threshold          = "10"
  alarm_description  = "This metric monitors error logs in the application"
  treat_missing_data = "notBreaching"

  tags = merge(var.tags, {
    Name = "vimbiso-pay-error-alarm-${var.environment}"
  })
}

# Add a time delay after cluster creation
resource "time_sleep" "wait_for_cluster" {
  depends_on = [aws_ecs_cluster.main]
  create_duration = "30s"
}

# Capacity Provider
resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name = aws_ecs_cluster.main.name

  capacity_providers = ["FARGATE", "FARGATE_SPOT"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}
