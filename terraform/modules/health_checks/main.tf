resource "aws_route53_health_check" "app" {
  fqdn              = var.alb_dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = var.health_check_path
  failure_threshold = "5"          # More tolerant of transient issues
  request_interval  = "30"         # Maximum allowed interval
  regions          = ["us-east-1", "eu-west-1", "ap-southeast-1"]  # Required minimum 3 regions

  tags = var.tags
}
