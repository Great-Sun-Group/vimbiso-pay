variable "environment" {
  description = "The deployment environment (development, production)"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
}

variable "az_count" {
  description = "Number of AZs to use"
  type        = number
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = []  # Will be computed from VPC CIDR if not provided
}
