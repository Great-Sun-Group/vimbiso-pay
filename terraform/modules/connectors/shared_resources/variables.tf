variable "environment" {
  description = "The deployment environment (development, staging, or production)"
  type        = string
}

variable "common_tags" {
  description = "Common tags to be applied to all resources"
  type        = map(string)
}

variable "domain" {
  description = "The full domain name for the ALB certificate"
  type        = string
}

variable "domain_base" {
  description = "The base domain for Route53 zone lookup"
  type        = string
}

variable "public_key" {
  description = "The public key for the EC2 key pair"
  type        = string
}

variable "vpc_cidr" {
  description = "The CIDR block for the VPC"
  type        = string
}

variable "az_count" {
  description = "Number of AZs to cover in a given region"
  type        = number
  default     = 2
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

# Verification system variables
variable "verification_photos_retention_days" {
  description = "Number of days to retain verification photos before archival"
  type        = number
  default     = 90
}

variable "verification_photos_expiration_days" {
  description = "Number of days to retain verification photos before deletion"
  type        = number
  default     = 365
}

variable "verification_temp_retention_days" {
  description = "Number of days to retain temporary verification files"
  type        = number
  default     = 1
}

variable "verification_processed_transition_days" {
  description = "Number of days before transitioning processed files to STANDARD_IA"
  type        = number
  default     = 30
}

variable "verification_processed_archive_days" {
  description = "Number of days before archiving processed files to Glacier"
  type        = number
  default     = 90
}
