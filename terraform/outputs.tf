# Infrastructure Outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.connectors.vpc_id
}

output "private_subnet_ids" {
  description = "The IDs of the private subnets"
  value       = module.connectors.private_subnet_ids
}

output "public_subnet_ids" {
  description = "The IDs of the public subnets"
  value       = module.connectors.public_subnet_ids
}

output "ecr_repository_url" {
  description = "The URL of the ECR repository"
  value       = module.connectors.ecr_repository_url
}

output "domain" {
  description = "The domain name for the environment"
  value       = module.connectors.domain
}

# Application Outputs
output "ecs_cluster_arn" {
  description = "The ARN of the ECS cluster"
  value       = module.app.ecs_cluster_arn
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  value       = module.app.ecs_cluster_name
}

output "ecs_service_name" {
  description = "The name of the ECS service"
  value       = module.app.ecs_service_name
}

output "ecs_service_id" {
  description = "The ID of the ECS service"
  value       = module.app.ecs_service_id
}

output "ecs_task_definition_arn" {
  description = "The ARN of the ECS task definition"
  value       = module.app.ecs_task_definition_arn
}

output "autoscaling_config" {
  description = "Auto scaling configuration"
  value = {
    min_capacity = module.app.autoscaling_target_min_capacity
    max_capacity = module.app.autoscaling_target_max_capacity
  }
}
