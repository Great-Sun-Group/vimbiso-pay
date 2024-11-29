variable "environment" {
  description = "The deployment environment (staging, production)"
  type        = string
}

variable "vpc_id" {
  description = "ID of the VPC"
  type        = string
}

variable "public_subnet_ids" {
  description = "List of public subnet IDs"
  type        = list(string)
}

variable "alb_security_group_id" {
  description = "Security group ID for the ALB"
  type        = string
}

variable "domain_name" {
  description = "The domain name for the environment"
  type        = string
}

variable "domain_zone_name" {
  description = "The Route53 zone name"
  type        = string
}

variable "health_check_path" {
  description = "Path for target group health check"
  type        = string
  default     = "/health/"
}

variable "health_check_port" {
  description = "Port for target group health check"
  type        = number
  default     = 8000
}

variable "deregistration_delay" {
  description = "Amount of time to wait for in-flight requests to complete before deregistering a target"
  type        = number
  default     = 60
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}
