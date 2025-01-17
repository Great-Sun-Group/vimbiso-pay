output "zone_id" {
  description = "The ID of the hosted zone"
  value       = local.zone_id
}

output "name_servers" {
  description = "The name servers for the hosted zone. These values need to be provided to the root domain administrator."
  value       = var.create_dns_records ? aws_route53_zone.app[0].name_servers : data.aws_route53_zone.existing[0].name_servers
}

output "domain_name" {
  description = "The domain name of the hosted zone"
  value       = var.domain_name
}

output "certificate_arn" {
  description = "ARN of the validated ACM certificate"
  value       = aws_acm_certificate_validation.app.certificate_arn
}

output "health_check_id" {
  description = "The ID of the Route53 health check"
  value       = var.create_dns_records ? aws_route53_health_check.app[0].id : null
}
