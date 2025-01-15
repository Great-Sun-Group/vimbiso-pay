variable "domain_name" {
  description = "The domain name for the certificate"
  type        = string
}

variable "environment" {
  description = "The environment (development/production)"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
