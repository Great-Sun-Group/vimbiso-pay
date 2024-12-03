# VPC Endpoints Security Group
resource "aws_security_group" "vpc_endpoints" {
  name        = "vimbiso-pay-vpc-endpoints-${var.environment}"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "Allow NFS traffic for EFS endpoint"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-vpc-endpoints-${var.environment}"
  })
}

# Application Load Balancer Security Group
resource "aws_security_group" "alb" {
  name        = "vimbiso-pay-alb-${var.environment}"
  description = "Controls access to the ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol    = "tcp"
    from_port   = 80
    to_port     = 80
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTP inbound"
  }

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow HTTPS inbound"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound"
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-alb-${var.environment}"
  })
}

# ECS Tasks Security Group
resource "aws_security_group" "ecs_tasks" {
  name        = "vimbiso-pay-ecs-tasks-${var.environment}"
  description = "Allow inbound access from the ALB only"
  vpc_id      = aws_vpc.main.id

  ingress {
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.alb.id]
    description     = "Allow inbound traffic from ALB"
  }

  ingress {
    protocol    = "tcp"
    from_port   = 6379
    to_port     = 6379
    self        = true
    description = "Allow Redis traffic between tasks"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound traffic"
  }

  # Explicit egress rule for EFS
  egress {
    protocol        = "tcp"
    from_port       = 2049
    to_port         = 2049
    security_groups = [aws_security_group.efs.id]
    description     = "Allow outbound NFS traffic to EFS"
  }

  # Explicit egress rule for EFS endpoint
  egress {
    protocol        = "tcp"
    from_port       = 2049
    to_port         = 2049
    security_groups = [aws_security_group.vpc_endpoints.id]
    description     = "Allow outbound NFS traffic to EFS endpoint"
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-ecs-tasks-${var.environment}"
  })
}

# EFS Security Group
resource "aws_security_group" "efs" {
  name        = "vimbiso-pay-efs-${var.environment}"
  description = "Allow inbound NFS traffic from ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from ECS tasks"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  # No explicit egress rules needed - return traffic is allowed by the stateful nature of security groups

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-efs-${var.environment}"
  })
}

# Add security group rules for VPC endpoints
resource "aws_security_group_rule" "vpc_endpoints_s3" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = aws_security_group.vpc_endpoints.id
  cidr_blocks       = [aws_vpc.main.cidr_block]
  description       = "Allow HTTPS inbound for S3 VPC endpoint"
}

resource "aws_security_group_rule" "vpc_endpoints_services" {
  type                     = "ingress"
  from_port                = 443
  to_port                  = 443
  protocol                 = "tcp"
  security_group_id        = aws_security_group.vpc_endpoints.id
  source_security_group_id = aws_security_group.ecs_tasks.id
  description             = "Allow HTTPS inbound for AWS services VPC endpoints (ECR, CloudWatch Logs)"
}
