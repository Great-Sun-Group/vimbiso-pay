output "certificate_arn" {
  description = "The ARN of the certificate"
  value       = aws_acm_certificate.app.arn
}

output "domain_name" {
  description = "The domain name for which the certificate was issued"
  value       = var.domain_name
}
