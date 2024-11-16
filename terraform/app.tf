module "app" {
  source = "./modules/app"

  environment                = var.environment
  aws_region                = local.current_env.aws_region
  common_tags               = {
    Environment = var.environment
    Project     = "Credex"
    ManagedBy   = "Terraform"
  }

  ecs_task_cpu              = local.current_env.ecs_task.cpu
  ecs_task_memory           = local.current_env.ecs_task.memory

  vpc_id                     = module.connectors.vpc_id
  subnet_ids                 = module.connectors.private_subnet_ids
  private_subnet_ids         = module.connectors.private_subnet_ids
  ecs_tasks_security_group_id = module.connectors.ecs_tasks_security_group_id
  alb_security_group_id      = module.connectors.alb_security_group_id
  target_group_arn           = module.connectors.target_group_arn
  alb_listener               = module.connectors.alb_listener

  ecr_repository_url         = module.connectors.ecr_repository_url
  docker_image              = var.docker_image
  ecs_execution_role_arn     = module.connectors.ecs_execution_role_arn
  ecs_task_role_arn          = module.connectors.ecs_task_role_arn
  cloudwatch_log_group_name  = module.connectors.cloudwatch_log_group_name

  neo_4j_ledger_space_bolt_url   = var.neo_4j_ledger_space_bolt_url
  neo_4j_search_space_bolt_url   = var.neo_4j_search_space_bolt_url
  neo_4j_ledger_space_user   = var.neo_4j_ledger_space_user
  neo_4j_search_space_user   = var.neo_4j_search_space_user
  neo_4j_ledger_space_password = var.neo_4j_ledger_space_password
  neo_4j_search_space_password = var.neo_4j_search_space_password
}
