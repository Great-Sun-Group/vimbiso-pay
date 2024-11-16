# ECS Cluster
output "ecs_cluster_arn" {
  description = "ARN of the ECS cluster"
  value       = aws_ecs_cluster.main.arn
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

# ECS Task Definition
output "ecs_task_definition_arn" {
  description = "ARN of the ECS task definition"
  value       = aws_ecs_task_definition.app.arn
}

output "ecs_task_definition_family" {
  description = "Family of the ECS task definition"
  value       = aws_ecs_task_definition.app.family
}

# ECS Service
output "ecs_service_name" {
  description = "Name of the ECS service"
  value       = aws_ecs_service.app.name
}

output "ecs_service_id" {
  description = "ID of the ECS service"
  value       = aws_ecs_service.app.id
}

# Auto Scaling
output "autoscaling_target_min_capacity" {
  description = "Minimum capacity of the auto scaling target"
  value       = aws_appautoscaling_target.app.min_capacity
}

output "autoscaling_target_max_capacity" {
  description = "Maximum capacity of the auto scaling target"
  value       = aws_appautoscaling_target.app.max_capacity
}
