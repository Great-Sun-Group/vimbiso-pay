output "repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.app.repository_url
}

output "repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.app.arn
}

output "repository_name" {
  description = "Name of the ECR repository"
  value       = aws_ecr_repository.app.name
}

output "repository_registry_id" {
  description = "Registry ID where the repository was created"
  value       = aws_ecr_repository.app.registry_id
}

output "repository_policy_id" {
  description = "ID of the repository policy"
  value       = aws_ecr_repository_policy.app.id
}

output "lifecycle_policy_id" {
  description = "ID of the lifecycle policy"
  value       = aws_ecr_lifecycle_policy.app.id
}
