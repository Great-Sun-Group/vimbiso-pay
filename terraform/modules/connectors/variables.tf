variable "environment" {
  description = "The deployment environment (staging, production)"
  type        = string

  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "Environment must be one of: production, staging"
  }
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}

variable "az_count" {
  description = "Number of AZs to use"
  type        = number
  default     = 2
}

variable "production_domain" {
  description = "The domain name for production environment"
  type        = string
}

variable "dev_domain_base" {
  description = "The base domain for non-production environments"
  type        = string
}

variable "environment_subdomains" {
  description = "Map of environment names to their subdomains"
  type        = map(string)
}

# Optional variables with defaults
variable "common_tags" {
  description = "Common tags to apply to all resources"
  type        = map(string)
  default     = {}
}
