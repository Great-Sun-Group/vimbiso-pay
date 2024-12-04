# S3 bucket for ALB logs
resource "aws_s3_bucket" "alb_logs" {
  bucket        = "vimbiso-pay-alb-logs-${var.environment}"
  force_destroy = var.environment != "production"

  tags = merge(var.tags, {
    Name = "vimbiso-pay-alb-logs-${var.environment}"
  })
}

# Data source for ELB service account
data "aws_elb_service_account" "current" {}

# Target Group for application
resource "aws_lb_target_group" "app" {
  name        = "vimbiso-pay-tg-${var.environment}"
  port        = 8000  # Match container port
  protocol    = "HTTP"  # Keep as HTTP since ALB handles SSL termination
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = var.health_check_path
    port                = "traffic-port"
    protocol            = "HTTP"  # Keep as HTTP since ALB handles SSL termination
    timeout             = 5  # Reduced from 15
    unhealthy_threshold = 3  # Reduced from 10
  }

  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
    enabled         = true
  }

  # Slow start gives targets time to warm up before receiving full share of requests
  slow_start = 30  # Reduced from 60 seconds

  tags = merge(var.tags, {
    Name = "vimbiso-pay-tg-${var.environment}"
  })

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      tags,
      stickiness
    ]
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  rule {
    id     = "log_expiration"
    status = "Enabled"

    expiration {
      days = 90
    }
  }
}

resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_elb_service_account.current.id}:root"
        }
        Action = "s3:PutObject"
        Resource = "${aws_s3_bucket.alb_logs.arn}/*"
      }
    ]
  })
}

# WAF Web ACL
resource "aws_wafv2_web_acl" "main" {
  name        = "vimbiso-pay-waf-${var.environment}"
  description = "WAF Web ACL for VimbisoPay ALB"
  scope       = "REGIONAL"

  default_action {
    allow {}
  }

  rule {
    name     = "AWSManagedRulesCommonRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesCommonRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedRulesCommonRuleSetMetric"
      sampled_requests_enabled  = true
    }
  }

  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 2

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "AWSManagedRulesKnownBadInputsRuleSetMetric"
      sampled_requests_enabled  = true
    }
  }

  rule {
    name     = "IPRateLimit"
    priority = 3

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name               = "IPRateLimitMetric"
      sampled_requests_enabled  = true
    }
  }

  visibility_config {
    cloudwatch_metrics_enabled = true
    metric_name               = "VimbisoPayWAFMetric"
    sampled_requests_enabled  = true
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-waf-${var.environment}"
  })

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      tags,
      description,
      rule,
      visibility_config
    ]
  }
}

# Application Load Balancer
resource "aws_lb" "main" {
  name               = "vimbiso-pay-alb-${var.environment}"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets           = var.public_subnet_ids

  # Enable access logs
  access_logs {
    bucket  = aws_s3_bucket.alb_logs.id
    enabled = true
  }

  # Enable deletion protection for production
  enable_deletion_protection = var.environment == "production"

  # Enable cross-zone load balancing
  enable_cross_zone_load_balancing = true

  tags = merge(var.tags, {
    Name = "vimbiso-pay-alb-${var.environment}"
  })

  lifecycle {
    prevent_destroy = true
    ignore_changes = [
      access_logs,
      tags,
      subnets  # Removed security_groups from ignore_changes
    ]
  }
}

# Associate WAF Web ACL with ALB
resource "aws_wafv2_web_acl_association" "main" {
  resource_arn = aws_lb.main.arn
  web_acl_arn  = aws_wafv2_web_acl.main.arn

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      web_acl_arn
    ]
  }
}

# HTTPS Listener with SSL termination and health check rule
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.main.arn
  port              = "443"
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS-1-2-2017-01"
  certificate_arn   = var.certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      default_action,
      ssl_policy,
      certificate_arn
    ]
  }
}

# HTTP Listener with health check rule
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }

  lifecycle {
    create_before_destroy = true
    ignore_changes = [
      default_action
    ]
  }
}

# Health check listener rule for HTTP
resource "aws_lb_listener_rule" "health_check_http" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }

  condition {
    path_pattern {
      values = ["/health/"]
    }
  }
}

# Health check listener rule for HTTPS
resource "aws_lb_listener_rule" "health_check_https" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 1

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }

  condition {
    path_pattern {
      values = ["/health/"]
    }
  }
}
