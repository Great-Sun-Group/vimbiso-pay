variable "environment" {
  description = "Environment (production/development)"
  type        = string
}

variable "domain_name" {
  description = "Domain name for the hosted zone"
  type        = string
}

variable "alb_dns_name" {
  description = "DNS name of the ALB"
  type        = string
  default     = null # Optional for certificate-only creation
}

variable "alb_zone_id" {
  description = "Zone ID of the ALB"
  type        = string
  default     = null # Optional for certificate-only creation
}

variable "health_check_path" {
  description = "Path for health checks"
  type        = string
  default     = "/health/"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "create_dns_records" {
  description = "Whether to create DNS records (A record and health check)"
  type        = bool
  default     = true
}
