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

  validation {
    condition     = var.az_count > 1
    error_message = "At least 2 AZs are required for high availability"
  }
}

variable "tags" {
  description = "Common resource tags"
  type        = map(string)
  default     = {}
}
