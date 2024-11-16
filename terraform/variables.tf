# Required variables
variable "environment" {
  description = "The deployment environment (development, staging, production)"
  type        = string

  validation {
    condition     = contains(["production", "development", "staging"], var.environment)
    error_message = "Environment must be one of: production, development, staging"
  }
}

variable "docker_image" {
  description = "The full Docker image to deploy (including repository and tag)"
  type        = string
}

# Neo4j related variables needed by databases module
variable "neo_4j_ledger_space_bolt_url" {
  description = "The Neo4j Bolt URL for Ledger Space"
  type        = string
  sensitive   = true
}

variable "neo_4j_search_space_bolt_url" {
  description = "The Neo4j Bolt URL for Search Space"
  type        = string
  sensitive   = true
}

variable "neo_4j_ledger_space_user" {
  description = "The username for the Neo4j Ledger Space"
  type        = string
  sensitive   = true
}

variable "neo_4j_search_space_user" {
  description = "The username for the Neo4j Search Space"
  type        = string
  sensitive   = true
}

variable "neo_4j_ledger_space_password" {
  description = "The password for the Neo4j Ledger Space"
  type        = string
  sensitive   = true
}

variable "neo_4j_search_space_password" {
  description = "The password for the Neo4j Search Space"
  type        = string
  sensitive   = true
}

variable "neo4j_enterprise_license" {
  description = "The Neo4j Enterprise License"
  type        = string
  sensitive   = true
}
