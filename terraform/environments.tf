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
  }

  # Domain configuration
  domain_config = {
    production = {
      dev_domain_base = local.production.dev_domain_base
      environment_subdomains = {
        production = local.production.subdomain
      }
    }
    staging = {
      dev_domain_base = local.staging.dev_domain_base
      environment_subdomains = {
        staging = local.staging.subdomain
      }
    }
  }

  # Get current domain config
  current_domain = local.domain_config[var.environment]
}
