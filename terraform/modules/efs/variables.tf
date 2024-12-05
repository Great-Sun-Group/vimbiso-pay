variable "environment" {
  description = "The deployment environment (staging, production)"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "efs_security_group_id" {
  description = "Security group ID for EFS"
  type        = string
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

variable "encrypted" {
  description = "Whether to enable EFS encryption"
  type        = bool
  default     = true
}

variable "performance_mode" {
  description = "EFS performance mode"
  type        = string
  default     = "generalPurpose"
}

variable "throughput_mode" {
  description = "EFS throughput mode"
  type        = string
  default     = "bursting"
}

variable "transition_to_ia" {
  description = "Lifecycle policy for transitioning to IA storage class"
  type        = string
  default     = "AFTER_30_DAYS"
}

variable "enable_backup" {
  description = "Whether to enable automatic backups"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 30
}
