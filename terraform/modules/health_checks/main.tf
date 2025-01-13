resource "aws_route53_health_check" "app" {
  fqdn              = var.alb_dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = var.health_check_path
  failure_threshold = "3"
  request_interval  = "30"
  regions          = ["us-east-1", "eu-west-1", "ap-southeast-1"]

  tags = var.tags
}
