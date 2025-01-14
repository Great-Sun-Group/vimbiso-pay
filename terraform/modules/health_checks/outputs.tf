output "health_check_id" {
  description = "ID of the created Route53 health check"
  value       = aws_route53_health_check.app.id
}
