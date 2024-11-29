variable "environment" {
  description = "The deployment environment (staging, production)"
  type        = string
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}

# Network Configuration
variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "ecs_tasks_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

# Load Balancer Configuration
variable "target_group_arn" {
  description = "ARN of the ALB target group"
  type        = string
}

# IAM Configuration
variable "execution_role_arn" {
  description = "ARN of the ECS task execution role"
  type        = string
}

variable "task_role_arn" {
  description = "ARN of the ECS task role"
  type        = string
}

# Container Configuration
variable "docker_image" {
  description = "Docker image to deploy"
  type        = string
}

variable "app_port" {
  description = "Port exposed by the application container"
  type        = number
  default     = 8000
}

variable "redis_port" {
  description = "Port exposed by the Redis container"
  type        = number
  default     = 6379
}

# Task Resource Configuration
variable "task_cpu" {
  description = "CPU units for the task"
  type        = number
}

variable "task_memory" {
  description = "Memory (MiB) for the task"
  type        = number
}

# EFS Configuration
variable "efs_file_system_id" {
  description = "ID of the EFS file system"
  type        = string
}

variable "app_access_point_id" {
  description = "ID of the app EFS access point"
  type        = string
}

variable "redis_access_point_id" {
  description = "ID of the Redis EFS access point"
  type        = string
}

# Auto Scaling Configuration
variable "min_capacity" {
  description = "Minimum number of tasks"
  type        = number
  default     = 2
}

variable "max_capacity" {
  description = "Maximum number of tasks"
  type        = number
  default     = 4
}

variable "cpu_threshold" {
  description = "CPU utilization threshold for scaling"
  type        = number
  default     = 80
}

variable "memory_threshold" {
  description = "Memory utilization threshold for scaling"
  type        = number
  default     = 80
}

# Environment Variables
variable "django_env" {
  description = "Django environment configuration"
  type = object({
    django_secret                         = string
    debug                                = bool
    mycredex_app_url                     = string
    client_api_key                       = string
    whatsapp_api_url                     = string
    whatsapp_access_token                = string
    whatsapp_phone_number_id             = string
    whatsapp_business_id                 = string
    whatsapp_registration_flow_id        = string
    whatsapp_company_registration_flow_id = string
  })
  sensitive = true
}

variable "allowed_hosts" {
  description = "List of allowed hosts for Django"
  type        = string
}

# CloudWatch Configuration
variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}
