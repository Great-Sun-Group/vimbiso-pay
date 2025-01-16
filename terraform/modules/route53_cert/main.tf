# Data source to fetch existing root zone with better error handling
data "aws_route53_zone" "root" {
  name         = regex("(?:[^.]+\\.)*([^.]+\\.[^.]+)$", var.domain_name)[0]
  private_zone = false
}

locals {
  # Add validation for domain name format
  domain_validation = regex("^[a-zA-Z0-9][a-zA-Z0-9-]*(\\.[a-zA-Z0-9][a-zA-Z0-9-]*)*$", var.domain_name)

  # Add debug outputs
  debug = {
    zone_name = data.aws_route53_zone.root.name
    zone_id   = data.aws_route53_zone.root.zone_id
  }
}

# Create ACM certificate with improved configuration
resource "aws_acm_certificate" "app" {
  domain_name               = var.domain_name
  validation_method         = "DNS"
  subject_alternative_names = []  # Explicitly empty to avoid validation complexity

  tags = merge(var.tags, {
    Name        = "vimbiso-pay-cert-${var.environment}"
    Environment = var.environment
    ManagedBy   = "terraform"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Create DNS validation record with improved configuration
resource "aws_route53_record" "cert_validation" {
  allow_overwrite = true
  name            = tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_name
  records         = [tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_value]
  type            = tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_type
  zone_id         = data.aws_route53_zone.root.zone_id
  ttl             = 300  # Increased TTL to reduce DNS propagation issues

  depends_on = [aws_acm_certificate.app]
}

# Validate the certificate with improved configuration
resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [aws_route53_record.cert_validation.fqdn]

  timeouts {
    create = "45m"  # Explicit timeout setting
  }

  depends_on = [aws_route53_record.cert_validation]
}

# Output debug information
output "certificate_validation_info" {
  value = {
    certificate_arn = aws_acm_certificate.app.arn
    domain_name    = var.domain_name
    zone_info      = local.debug
    validation_fqdn = aws_route53_record.cert_validation.fqdn
  }
  description = "Debug information for certificate validation"
}
