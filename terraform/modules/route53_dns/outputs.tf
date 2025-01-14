output "zone_id" {
  description = "The ID of the hosted zone"
  value       = var.create_dns_records ? aws_route53_zone.app[0].zone_id : null
}

output "nameservers" {
  description = "The nameservers for the hosted zone"
  value       = var.create_dns_records ? aws_route53_zone.app[0].name_servers : []
}

output "domain_name" {
  description = "The domain name"
  value       = var.domain_name
}
