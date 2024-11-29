output "ecs_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_execution_role.arn
}

output "ecs_execution_role_name" {
  description = "Name of the ECS task execution role"
  value       = aws_iam_role.ecs_execution_role.name
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task_role.arn
}

output "ecs_task_role_name" {
  description = "Name of the ECS task role"
  value       = aws_iam_role.ecs_task_role.name
}

output "execution_role_policy_ids" {
  description = "List of policy IDs attached to the execution role"
  value = {
    managed = aws_iam_role_policy_attachment.ecs_execution_role_policy.id
    custom  = aws_iam_role_policy.ecs_execution_extra.id
  }
}

output "task_role_policy_ids" {
  description = "List of policy IDs attached to the task role"
  value = {
    efs        = aws_iam_role_policy.ecs_task_efs.id
    cloudwatch = aws_iam_role_policy.ecs_task_cloudwatch.id
  }
}
