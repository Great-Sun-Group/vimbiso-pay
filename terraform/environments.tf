# Load environment configurations from external JSON files
data "local_file" "production" {
  filename = "${path.module}/environments/production.json"
}

data "local_file" "staging" {
  filename = "${path.module}/environments/staging.json"
}

locals {
  # Parse JSON content from files
  production = jsondecode(data.local_file.production.content)
  staging    = jsondecode(data.local_file.staging.content)

  # Environment configuration map
  env_config = {
    production = local.production
    staging    = local.staging
  }

  # Get current environment config
  current_env = local.env_config[var.environment]

  # Common tags for all resources
  common_tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = "vimbiso-pay"
    Application = "whatsapp-bot"
  }
}
