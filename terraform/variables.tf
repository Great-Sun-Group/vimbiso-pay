# Required Environment Variables
variable "environment" {
  description = "The deployment environment (staging, production)"
  type        = string

  validation {
    condition     = contains(["production", "staging"], var.environment)
    error_message = "Environment must be one of: production, staging"
  }
}

# Application Configuration
variable "docker_image" {
  description = "The full Docker image to deploy (including repository and tag)"
  type        = string
}

# Django Environment Variables
variable "django_secret" {
  description = "Django secret key"
  type        = string
  sensitive   = true
}

variable "debug" {
  description = "Django debug mode"
  type        = bool
  default     = false
}

variable "mycredex_app_url" {
  description = "URL for the VimbisoPay WhatsApp Chatbot"
  type        = string
}

# WhatsApp Integration Variables
variable "client_api_key" {
  description = "API key for WhatsApp bot"
  type        = string
  sensitive   = true
}

variable "whatsapp_api_url" {
  description = "WhatsApp API URL"
  type        = string
}

variable "whatsapp_access_token" {
  description = "WhatsApp access token"
  type        = string
  sensitive   = true
}

variable "whatsapp_phone_number_id" {
  description = "WhatsApp phone number ID"
  type        = string
  sensitive   = true
}

variable "whatsapp_business_id" {
  description = "WhatsApp business ID"
  type        = string
  sensitive   = true
}

variable "whatsapp_registration_flow_id" {
  description = "WhatsApp registration flow ID"
  type        = string
  sensitive   = true
}

variable "whatsapp_company_registration_flow_id" {
  description = "WhatsApp company registration flow ID"
  type        = string
  sensitive   = true
}
