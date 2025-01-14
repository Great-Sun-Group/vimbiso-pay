resource "aws_route53_health_check" "app" {
  fqdn              = var.alb_dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = var.health_check_path
  failure_threshold = "5"          # More tolerant of transient issues
  request_interval  = "60"         # Reduced check frequency
  regions          = ["us-east-1"] # Single region check for simplicity

  tags = var.tags
}
