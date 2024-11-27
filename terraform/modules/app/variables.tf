variable "environment" {
  description = "The deployment environment (staging, production)"
  type        = string
}

variable "aws_region" {
  description = "The AWS region to deploy to"
  type        = string
}

variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
}

# ECS Configuration
variable "ecs_task_cpu" {
  description = "CPU units for the ECS task (1024 = 1 vCPU)"
  type        = string
}

variable "ecs_task_memory" {
  description = "Memory for the ECS task in MiB"
  type        = string
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

variable "target_group_arn" {
  description = "ARN of the target group"
  type        = string
}

# Container Configuration
variable "docker_image" {
  description = "Docker image to deploy"
  type        = string
}

variable "ecs_execution_role_arn" {
  description = "ARN of the ECS execution role"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  type        = string
}

variable "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  type        = string
}

# Application Environment Variables
variable "django_secret" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "mycredex_app_url" {
  description = "URL for the Credex Core API"
  type        = string
}

variable "client_api_key" {
  description = "API key for WhatsApp bot"
  type        = string
  sensitive   = true
}

variable "whatsapp_api_url" {
  description = "WhatsApp API URL"
  type        = string
}

variable "whatsapp_access_token" {
  description = "WhatsApp access token"
  type        = string
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp phone number ID"
  type        = string
  sensitive   = true
}
