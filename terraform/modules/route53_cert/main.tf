# Data source to fetch existing root zone
data "aws_route53_zone" "root" {
  name         = regex("(?:[^.]+\\.)*([^.]+\\.[^.]+)$", var.domain_name)[0]
  private_zone = false
}

# Create ACM certificate
resource "aws_acm_certificate" "app" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  tags = merge(var.tags, {
    Name = "vimbiso-pay-cert-${var.environment}"
  })

  lifecycle {
    create_before_destroy = true
  }
}

# Create DNS validation record in the root zone
resource "aws_route53_record" "cert_validation" {
  allow_overwrite = true
  name            = tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_name
  records         = [tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_value]
  type            = tolist(aws_acm_certificate.app.domain_validation_options)[0].resource_record_type
  zone_id         = data.aws_route53_zone.root.zone_id
  ttl             = 60
}

# Validate the certificate
resource "aws_acm_certificate_validation" "app" {
  certificate_arn         = aws_acm_certificate.app.arn
  validation_record_fqdns = [aws_route53_record.cert_validation.fqdn]
}
