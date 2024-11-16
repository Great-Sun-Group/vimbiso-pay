output "vpc_id" {
  value       = module.shared_resources.vpc_id
  description = "The ID of the VPC"
}

output "private_subnet_ids" {
  value       = module.shared_resources.private_subnet_ids
  description = "The IDs of the private subnets"
}

output "public_subnet_ids" {
  value       = module.shared_resources.public_subnet_ids
  description = "The IDs of the public subnets"
}

output "subnet_ids" {
  value       = concat(module.shared_resources.private_subnet_ids, module.shared_resources.public_subnet_ids)
  description = "The IDs of all subnets (private and public)"
}

output "neo4j_security_group_id" {
  value       = module.shared_resources.neo4j_security_group_id
  description = "The ID of the Neo4j security group"
}

output "key_pair_name" {
  value       = module.shared_resources.key_pair_name
  description = "The name of the key pair"
}

output "alb_security_group_id" {
  value       = module.shared_resources.alb_security_group_id
  description = "The ID of the ALB security group"
}

output "ecs_tasks_security_group_id" {
  value       = module.shared_resources.ecs_tasks_security_group_id
  description = "The ID of the ECS tasks security group"
}

output "alb_dns_name" {
  value       = module.shared_resources.alb_dns_name
  description = "The DNS name of the Application Load Balancer"
}

output "target_group_arn" {
  value       = module.shared_resources.target_group_arn
  description = "The ARN of the target group"
}

output "alb_listener" {
  value       = module.shared_resources.alb_listener
  description = "The ARN of the ALB listener"
}

output "ecr_repository_url" {
  value       = module.shared_resources.ecr_repository_url
  description = "The URL of the ECR repository"
}

output "ecs_execution_role_arn" {
  value       = module.shared_resources.ecs_execution_role_arn
  description = "The ARN of the ECS execution role"
}

output "ecs_task_role_arn" {
  value       = module.shared_resources.ecs_task_role_arn
  description = "The ARN of the ECS task role"
}

output "cloudwatch_log_group_name" {
  value       = module.shared_resources.cloudwatch_log_group_name
  description = "The name of the CloudWatch log group"
}
