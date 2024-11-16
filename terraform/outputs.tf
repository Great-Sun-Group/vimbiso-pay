# VPC outputs
output "vpc_id" {
  value       = module.connectors.vpc_id
  description = "The ID of the VPC"
}

output "subnet_ids" {
  value       = module.connectors.subnet_ids
  description = "The IDs of all subnets (private and public)"
}

output "neo4j_security_group_id" {
  value       = module.connectors.neo4j_security_group_id
  description = "The ID of the Neo4j security group"
}

output "key_pair_name" {
  value       = module.connectors.key_pair_name
  description = "The name of the key pair"
}

output "alb_security_group_id" {
  value       = module.connectors.alb_security_group_id
  description = "The ID of the ALB security group"
}

# ECS outputs
output "ecs_cluster_arn" {
  value       = module.app.ecs_cluster_arn
  description = "The ARN of the ECS cluster"
}

output "ecs_task_definition_arn" {
  value       = module.app.ecs_task_definition_arn
  description = "The ARN of the ECS task definition"
}

output "ecs_service_name" {
  value       = module.app.ecs_service_name
  description = "The name of the ECS service"
}

output "ecs_service_id" {
  value       = module.app.ecs_service_id
  description = "The ID of the ECS service"
}
