# Create the hosted zone for the environment
resource "aws_route53_zone" "app" {
  count = var.create_dns_records ? 1 : 0
  name  = var.domain_name

  tags = merge(var.tags, {
    Name = "vimbiso-pay-zone-${var.environment}"
  })
}

# Create A record for the application
resource "aws_route53_record" "app" {
  count = var.create_dns_records ? 1 : 0

  zone_id = aws_route53_zone.app[0].zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }
}

# Create health check for the application
resource "aws_route53_health_check" "app" {
  count = var.create_dns_records ? 1 : 0

  fqdn              = var.alb_dns_name
  port              = 443
  type              = "HTTPS"
  resource_path     = var.health_check_path
  failure_threshold = "3"
  request_interval  = "30"
  regions          = ["us-east-1", "eu-west-1", "ap-southeast-1"]

  tags = merge(var.tags, {
    Name = "vimbiso-pay-health-${var.environment}"
  })
}
