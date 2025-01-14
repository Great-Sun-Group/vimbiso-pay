variable "alb_dns_name" {
  description = "The DNS name of the ALB"
  type        = string
}

variable "health_check_path" {
  description = "The path for health checks"
  type        = string
  default     = "/health/"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
