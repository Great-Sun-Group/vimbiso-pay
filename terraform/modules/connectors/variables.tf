variable "environment" {
  description = "The deployment environment (development, staging, production, etc)"
  type        = string
}

variable "aws_region" {
  description = "The AWS region to deploy to"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
}

variable "production_domain" {
  description = "The domain for production environment"
  type        = string
}

variable "dev_domain_base" {
  description = "The base domain for non-production environments"
  type        = string
  default     = null
}

variable "environment_subdomains" {
  description = "Map of environment names to their subdomains on mycredex.dev (production not included)"
  type        = map(string)
}

variable "common_tags" {
  description = "Common tags to be applied to all resources"
  type        = map(string)
}

variable "create_vpc" {
  description = "Whether to create the VPC"
  type        = bool
  default     = true
}

variable "create_subnets" {
  description = "Whether to create the subnets"
  type        = bool
  default     = true
}

variable "create_igw" {
  description = "Whether to create the Internet Gateway"
  type        = bool
  default     = true
}

variable "create_nat" {
  description = "Whether to create the NAT Gateway"
  type        = bool
  default     = true
}

variable "create_routes" {
  description = "Whether to create the route tables"
  type        = bool
  default     = true
}

variable "create_sg" {
  description = "Whether to create the security groups"
  type        = bool
  default     = true
}

variable "create_ecr" {
  description = "Whether to create the ECR repository"
  type        = bool
  default     = true
}

variable "create_ecs" {
  description = "Whether to create the ECS cluster"
  type        = bool
  default     = true
}

variable "create_logs" {
  description = "Whether to create the CloudWatch log group"
  type        = bool
  default     = true
}

variable "create_iam" {
  description = "Whether to create the IAM roles"
  type        = bool
  default     = true
}

variable "create_key_pair" {
  description = "Whether to create the key pair"
  type        = bool
  default     = true
}

variable "create_load_balancer" {
  description = "Whether to create the load balancer"
  type        = bool
  default     = true
}

variable "create_target_group" {
  description = "Whether to create the target group"
  type        = bool
  default     = true
}

variable "create_security_groups" {
  description = "Whether to create security groups"
  type        = bool
  default     = true
}

variable "create_neo4j_security_group" {
  description = "Whether to create the Neo4j security group"
  type        = bool
  default     = true
}

variable "create_acm" {
  description = "Whether to create the ACM certificate"
  type        = bool
  default     = true
}

variable "public_key" {
  description = "The public key for the EC2 key pair"
  type        = string
}
