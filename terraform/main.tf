# Networking Module
module "networking" {
  source = "./modules/networking"

  environment = var.environment
  vpc_cidr    = local.current_env.vpc_cidr
  az_count    = local.current_env.az_count
  tags        = local.common_tags
}

# Load Balancer Module
module "loadbalancer" {
  source = "./modules/loadbalancer"

  environment         = var.environment
  vpc_id             = module.networking.vpc_id
  public_subnet_ids  = module.networking.public_subnet_ids
  alb_security_group_id = module.networking.alb_security_group_id
  domain_name        = "${local.current_domain.environment_subdomains[var.environment]}.${local.current_domain.dev_domain_base}"
  domain_zone_name   = local.current_domain.dev_domain_base
  health_check_path  = "/health/"
  health_check_port  = 8000
  tags               = local.common_tags
}

# EFS Module
module "efs" {
  source = "./modules/efs"

  environment         = var.environment
  private_subnet_ids = module.networking.private_subnet_ids
  efs_security_group_id = module.networking.efs_security_group_id
  tags               = local.common_tags
}

# IAM Module
module "iam" {
  source = "./modules/iam"

  environment            = var.environment
  efs_file_system_arn   = module.efs.file_system_arn
  app_access_point_arn  = module.efs.app_access_point_arn
  redis_access_point_arn = module.efs.redis_access_point_arn
  cloudwatch_log_group_arn = "arn:aws:logs:${local.current_env.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/ecs/vimbiso-pay-${var.environment}:*"
  region                = local.current_env.aws_region
  account_id            = data.aws_caller_identity.current.account_id
  tags                  = local.common_tags
}

# ECR Module
module "ecr" {
  source = "./modules/ecr"

  environment = var.environment
  tags       = local.common_tags
}

# ECS Module
module "ecs" {
  source = "./modules/ecs"

  environment                = var.environment
  vpc_id                     = module.networking.vpc_id
  private_subnet_ids         = module.networking.private_subnet_ids
  ecs_tasks_security_group_id = module.networking.ecs_tasks_security_group_id
  target_group_arn           = module.loadbalancer.target_group_arn
  execution_role_arn         = module.iam.ecs_execution_role_arn
  task_role_arn             = module.iam.ecs_task_role_arn
  docker_image              = var.docker_image
  efs_file_system_id        = module.efs.file_system_id
  app_access_point_id       = module.efs.app_access_point_id
  redis_access_point_id     = module.efs.redis_access_point_id
  task_cpu                  = local.current_env.ecs_task.cpu
  task_memory               = local.current_env.ecs_task.memory
  min_capacity              = local.current_env.autoscaling.min_capacity
  max_capacity              = local.current_env.autoscaling.max_capacity
  cpu_threshold             = local.current_env.autoscaling.cpu_threshold
  memory_threshold          = local.current_env.autoscaling.memory_threshold
  allowed_hosts            = "*.amazonaws.com,${module.loadbalancer.alb_dns_name},${local.current_domain.environment_subdomains[var.environment]}.${local.current_domain.dev_domain_base}"

  django_env = {
    django_secret                         = var.django_secret
    debug                                = var.debug
    mycredex_app_url                     = var.mycredex_app_url
    client_api_key                       = var.client_api_key
    whatsapp_api_url                     = var.whatsapp_api_url
    whatsapp_access_token                = var.whatsapp_access_token
    whatsapp_phone_number_id             = var.whatsapp_phone_number_id
    whatsapp_business_id                 = var.whatsapp_business_id
    whatsapp_registration_flow_id        = var.whatsapp_registration_flow_id
    whatsapp_company_registration_flow_id = var.whatsapp_company_registration_flow_id
  }

  tags = local.common_tags
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}
