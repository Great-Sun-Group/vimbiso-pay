variable "domain_name" {
  description = "The domain name for the DNS records"
  type        = string
}

variable "environment" {
  description = "The environment (staging/production)"
  type        = string
}

variable "create_dns_records" {
  description = "Whether to create DNS records"
  type        = bool
  default     = true
}

variable "alb_dns_name" {
  description = "The DNS name of the ALB"
  type        = string
}

variable "alb_zone_id" {
  description = "The hosted zone ID of the ALB"
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
