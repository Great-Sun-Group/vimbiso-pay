# Create the hosted zone for the environment
resource "aws_route53_zone" "app" {
  count = var.create_dns_records ? 1 : 0
  name  = var.domain_name

  tags = merge(var.tags, {
    Name = "vimbiso-pay-zone-${var.environment}"
  })
}

# Data source to fetch root zone
data "aws_route53_zone" "root" {
  name         = regex("(?:[^.]+\\.)*([^.]+\\.[^.]+)$", var.domain_name)[0]
  private_zone = false
}

# Create NS record in root zone to delegate to our environment zone
resource "aws_route53_record" "ns" {
  count = var.create_dns_records ? 1 : 0

  zone_id = data.aws_route53_zone.root.zone_id
  name    = var.domain_name
  type    = "NS"
  ttl     = "30"

  records = aws_route53_zone.app[0].name_servers
}

# Create weighted A record for the application
resource "aws_route53_record" "app" {
  count = var.create_dns_records ? 1 : 0

  zone_id = aws_route53_zone.app[0].zone_id
  name    = var.domain_name
  type    = "A"

  weighted_routing_policy {
    weight = 100
  }
  set_identifier = "primary"

  alias {
    name                   = var.alb_dns_name
    zone_id                = var.alb_zone_id
    evaluate_target_health = true
  }

  health_check_id = var.health_check_id
}
