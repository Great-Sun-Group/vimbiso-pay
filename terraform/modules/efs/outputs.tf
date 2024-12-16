output "file_system_id" {
  description = "ID of the EFS file system"
  value       = aws_efs_file_system.main.id
}

output "file_system_arn" {
  description = "ARN of the EFS file system"
  value       = aws_efs_file_system.main.arn
}

output "mount_target_ids" {
  description = "List of mount target IDs"
  value       = aws_efs_mount_target.main[*].id
}

output "app_access_point_id" {
  description = "ID of the app data access point"
  value       = aws_efs_access_point.app_data.id
}

output "app_access_point_arn" {
  description = "ARN of the app data access point"
  value       = aws_efs_access_point.app_data.arn
}

output "redis_cache_access_point_id" {
  description = "ID of the Redis cache access point"
  value       = aws_efs_access_point.redis_cache.id
}

output "redis_cache_access_point_arn" {
  description = "ARN of the Redis cache access point"
  value       = aws_efs_access_point.redis_cache.arn
}

output "redis_state_access_point_id" {
  description = "ID of the Redis state access point"
  value       = aws_efs_access_point.redis_state.id
}

output "redis_state_access_point_arn" {
  description = "ARN of the Redis state access point"
  value       = aws_efs_access_point.redis_state.arn
}
