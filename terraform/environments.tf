# Load environment configurations from external JSON files
data "local_file" "production" {
  filename = "${path.module}/environments/production.json"
}

data "local_file" "development" {
  filename = "${path.module}/environments/development.json"
}

data "local_file" "staging" {
  filename = "${path.module}/environments/staging.json"
}

locals {
  # Parse JSON content from files
  production  = jsondecode(data.local_file.production.content)
  development = jsondecode(data.local_file.development.content)
  staging     = jsondecode(data.local_file.staging.content)

  # Environment configuration map
  env_config = {
    production  = local.production
    development = local.development
    staging     = local.staging
  }

  # Get current environment config
  current_env = local.env_config[var.environment]

  # Common tags for all resources
  common_tags = {
    Environment = var.environment
    ManagedBy  = "terraform"
    Project    = "credex-core"
  }
}
