# Cluster Outputs
output "cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

# Service Discovery Outputs
output "service_discovery_namespace_id" {
  description = "ID of the service discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.main.id
}

output "service_discovery_namespace_arn" {
  description = "ARN of the service discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.main.arn
}

output "service_discovery_namespace_name" {
  description = "Name of the service discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.main.name
}

output "app_service_discovery_service_arn" {
  description = "ARN of the app service discovery service"
  value       = aws_service_discovery_service.app.arn
}

output "redis_service_discovery_service_arn" {
  description = "ARN of the Redis service discovery service"
  value       = aws_service_discovery_service.redis.arn
}

# CloudWatch Outputs
output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.app.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.app.arn
}

output "cloudwatch_dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_name
}

output "cloudwatch_dashboard_arn" {
  description = "ARN of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.main.dashboard_arn
}

# Metric Alarms
output "cpu_alarm_arn" {
  description = "ARN of the CPU utilization alarm"
  value       = aws_cloudwatch_metric_alarm.cluster_cpu_high.arn
}

output "memory_alarm_arn" {
  description = "ARN of the memory utilization alarm"
  value       = aws_cloudwatch_metric_alarm.cluster_memory_high.arn
}

# Metric Filters
output "error_metric_filter_name" {
  description = "Name of the error metric filter"
  value       = aws_cloudwatch_log_metric_filter.error_logs.name
}

output "container_insights_metric_filter_name" {
  description = "Name of the Container Insights metric filter"
  value       = aws_cloudwatch_log_metric_filter.container_insights.name
}

# Container Insights Status
output "container_insights_status" {
  description = "Status of Container Insights for the cluster"
  value       = [for s in aws_ecs_cluster.main.setting : s.value if s.name == "containerInsights"][0]
}

# Default Capacity Provider Strategy
output "default_capacity_provider_strategy" {
  description = "Default capacity provider strategy for the cluster"
  value = [for s in aws_ecs_cluster_capacity_providers.main.default_capacity_provider_strategy : {
    capacity_provider = s.capacity_provider
    weight           = s.weight
    base             = s.base
  }][0]
}

# Region Information
output "aws_region" {
  description = "AWS region where the cluster is deployed"
  value       = data.aws_region.current.name
}

# Tags
output "cluster_tags" {
  description = "Tags applied to the ECS cluster"
  value       = aws_ecs_cluster.main.tags_all
}
