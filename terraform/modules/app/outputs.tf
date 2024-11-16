# Outputs for the app module

output "ecs_cluster_arn" {
  value       = aws_ecs_cluster.credex_cluster.arn
  description = "The ARN of the ECS cluster"
}

output "ecs_task_definition_arn" {
  value       = aws_ecs_task_definition.credex_core.arn
  description = "The ARN of the ECS task definition"
}

output "ecs_service_name" {
  value       = aws_ecs_service.credex_core.name
  description = "The name of the ECS service"
}

output "ecs_service_id" {
  value       = aws_ecs_service.credex_core.id
  description = "The ID of the ECS service"
}
