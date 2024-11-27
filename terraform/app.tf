# Infrastructure Module
module "connectors" {
  source = "./modules/connectors"

  environment            = var.environment
  vpc_cidr              = local.current_env.vpc_cidr
  az_count              = local.current_env.az_count
  production_domain     = local.current_domain.domain
  dev_domain_base       = local.current_domain.dev_domain_base
  environment_subdomains = local.current_domain.environment_subdomains
  common_tags           = local.common_tags
}

# Application Module
module "app" {
  source = "./modules/app"

  environment                = var.environment
  aws_region                = local.current_env.aws_region
  common_tags               = local.common_tags

  # ECS Configuration
  ecs_task_cpu              = local.current_env.ecs_task.cpu
  ecs_task_memory           = local.current_env.ecs_task.memory

  # Network Configuration
  vpc_id                     = module.connectors.vpc_id
  private_subnet_ids         = module.connectors.private_subnet_ids
  ecs_tasks_security_group_id = module.connectors.ecs_tasks_security_group_id
  target_group_arn           = module.connectors.target_group_arn

  # Container Configuration
  docker_image              = var.docker_image
  ecs_execution_role_arn    = module.connectors.ecs_execution_role_arn
  ecs_task_role_arn         = module.connectors.ecs_task_role_arn
  cloudwatch_log_group_name = module.connectors.cloudwatch_log_group_name

  # Application Environment Variables
  django_secret            = var.django_secret
  mycredex_app_url        = var.mycredex_app_url
  client_api_key    = var.client_api_key
  whatsapp_api_url        = var.whatsapp_api_url
  whatsapp_access_token   = var.whatsapp_access_token
  whatsapp_phone_number_id = var.whatsapp_phone_number_id
}
