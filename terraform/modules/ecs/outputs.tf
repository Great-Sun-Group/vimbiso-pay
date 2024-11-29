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

output "service_id" {
  description = "ID of the ECS service"
  value       = aws_ecs_service.app.id
}

output "service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.app.name
}

output "task_definition_arn" {
  description = "ARN of the task definition"
  value       = aws_ecs_task_definition.app.arn
}

output "task_definition_family" {
  description = "Family of the task definition"
  value       = aws_ecs_task_definition.app.family
}

output "task_definition_revision" {
  description = "Revision of the task definition"
  value       = aws_ecs_task_definition.app.revision
}

output "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.app.name
}

output "cloudwatch_log_group_arn" {
  description = "ARN of the CloudWatch log group"
  value       = aws_cloudwatch_log_group.app.arn
}

output "service_discovery_namespace_id" {
  description = "ID of the service discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.app.id
}

output "service_discovery_namespace_arn" {
  description = "ARN of the service discovery namespace"
  value       = aws_service_discovery_private_dns_namespace.app.arn
}

output "service_discovery_service_arn" {
  description = "ARN of the service discovery service"
  value       = aws_service_discovery_service.app.arn
}

output "autoscaling_target_id" {
  description = "ID of the App Autoscaling target"
  value       = aws_appautoscaling_target.app.id
}

output "autoscaling_policies" {
  description = "Map of autoscaling policy ARNs"
  value = {
    cpu      = aws_appautoscaling_policy.cpu.arn
    memory   = aws_appautoscaling_policy.memory.arn
    requests = aws_appautoscaling_policy.requests.arn
  }
}

output "cloudwatch_alarms" {
  description = "Map of CloudWatch alarm ARNs"
  value = {
    cpu_high    = aws_cloudwatch_metric_alarm.cpu_high.arn
    memory_high = aws_cloudwatch_metric_alarm.memory_high.arn
    error_logs  = aws_cloudwatch_metric_alarm.error_logs.arn
  }
}
