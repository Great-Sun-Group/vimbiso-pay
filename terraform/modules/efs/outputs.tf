output "file_system_id" {
  description = "ID of the EFS file system"
  value       = aws_efs_file_system.main.id
}

output "file_system_arn" {
  description = "ARN of the EFS file system"
  value       = aws_efs_file_system.main.arn
}

output "app_access_point_id" {
  description = "ID of the app data access point"
  value       = aws_efs_access_point.app_data.id
}

output "app_access_point_arn" {
  description = "ARN of the app data access point"
  value       = aws_efs_access_point.app_data.arn
}

output "redis_access_point_id" {
  description = "ID of the Redis data access point"
  value       = aws_efs_access_point.redis_data.id
}

output "redis_access_point_arn" {
  description = "ARN of the Redis data access point"
  value       = aws_efs_access_point.redis_data.arn
}

output "mount_target_ids" {
  description = "List of mount target IDs"
  value       = aws_efs_mount_target.main[*].id
}

output "mount_target_dns_names" {
  description = "List of mount target DNS names"
  value       = [for mt in aws_efs_mount_target.main : mt.dns_name]
}

output "mount_target_network_interface_ids" {
  description = "List of mount target network interface IDs"
  value       = [for mt in aws_efs_mount_target.main : mt.network_interface_id]
}
