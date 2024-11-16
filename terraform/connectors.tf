module "connectors" {
  source = "./modules/connectors"

  environment = var.environment
  aws_region  = local.current_env.aws_region

  # Domain configuration
  production_domain     = local.env_config.production.domain
  dev_domain_base      = var.environment == "production" ? null : local.current_env.dev_domain_base
  environment_subdomains = {
    for k, v in local.env_config : k => v.subdomain if k != "production"
  }

  # Network configuration
  vpc_cidr = local.current_env.vpc_cidr

  # Feature flags - hardcoded since they're always true
  create_vpc                 = true
  create_subnets            = true
  create_igw                = true
  create_nat                = true
  create_routes             = true
  create_sg                 = true
  create_ecr                = true
  create_ecs                = true
  create_logs               = true
  create_iam                = true
  create_key_pair           = true
  create_load_balancer      = true
  create_target_group       = true
  create_security_groups    = true
  create_neo4j_security_group = true
  create_acm                = true

  # Tags
  common_tags = local.common_tags

  public_key = tls_private_key.ssh.public_key_openssh
}

# Generate SSH key
resource "tls_private_key" "ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}
