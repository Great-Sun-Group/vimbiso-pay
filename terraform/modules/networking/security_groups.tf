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
  }

  ingress {
    protocol    = "tcp"
    from_port   = 443
    to_port     = 443
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
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
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id

  # Allow inbound traffic from ALB to application port
  ingress {
    protocol        = "tcp"
    from_port       = 8000
    to_port         = 8000
    security_groups = [aws_security_group.alb.id]
    description     = "Allow inbound traffic from ALB"
  }

  # Allow Redis traffic between tasks
  ingress {
    protocol    = "tcp"
    from_port   = 6379
    to_port     = 6379
    self        = true
    description = "Allow Redis traffic between tasks"
  }

  # Allow all traffic within the security group
  ingress {
    protocol  = -1
    from_port = 0
    to_port   = 0
    self      = true
    description = "Allow all traffic between tasks"
  }

  # Allow outbound internet access
  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow inbound health checks from VPC CIDR
  ingress {
    protocol    = "tcp"
    from_port   = 8000
    to_port     = 8000
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Allow health checks from VPC"
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
  description = "Security group for EFS mount targets"
  vpc_id      = aws_vpc.main.id

  # Allow NFS traffic from ECS tasks
  ingress {
    protocol        = "tcp"
    from_port       = 2049
    to_port         = 2049
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "Allow NFS from ECS tasks"
  }

  # Allow NFS traffic from the VPC CIDR
  ingress {
    protocol    = "tcp"
    from_port   = 2049
    to_port     = 2049
    cidr_blocks = [aws_vpc.main.cidr_block]
    description = "Allow NFS from VPC CIDR"
  }

  egress {
    protocol    = "-1"
    from_port   = 0
    to_port     = 0
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(var.tags, {
    Name = "vimbiso-pay-efs-${var.environment}"
  })
}

# VPC Endpoints Security Group
resource "aws_security_group" "vpc_endpoints" {
  name        = "vimbiso-pay-vpc-endpoints-${var.environment}"
  description = "Security group for VPC endpoints"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
    description     = "Allow HTTPS from ECS tasks"
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
