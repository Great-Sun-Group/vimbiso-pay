# Permission boundary policy
resource "aws_iam_policy" "permission_boundary" {
  name        = "vimbiso-pay-permission-boundary-${var.environment}"
  description = "Permission boundary for VimbisoPay ECS roles"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Deny"
        Action = [
          "iam:CreateUser",
          "iam:DeleteUser",
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:CreatePolicy",
          "iam:DeletePolicy"
        ]
        Resource = "*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "vimbiso-pay-permission-boundary-${var.environment}"
  })
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_execution_role" {
  name                 = "vimbiso-pay-ecs-execution-${var.environment}"
  path                 = "/service-role/"
  permissions_boundary = aws_iam_policy.permission_boundary.arn

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "vimbiso-pay-ecs-execution-${var.environment}"
  })
}

# Attach AWS managed policy for ECS task execution
resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ECS Task Role
resource "aws_iam_role" "ecs_task_role" {
  name                 = "vimbiso-pay-ecs-task-${var.environment}"
  path                 = "/service-role/"
  permissions_boundary = aws_iam_policy.permission_boundary.arn

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name = "vimbiso-pay-ecs-task-${var.environment}"
  })
}

# EFS access policy for task role with explicit deny
resource "aws_iam_role_policy" "ecs_task_efs" {
  name = "vimbiso-pay-ecs-task-efs-${var.environment}"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "elasticfilesystem:ClientMount",
          "elasticfilesystem:ClientWrite"
        ]
        Resource = var.efs_file_system_arn
        Condition = {
          StringEquals = {
            "elasticfilesystem:AccessPointArn" = [
              var.app_access_point_arn,
              var.redis_access_point_arn
            ]
          }
        }
      },
      {
        Effect = "Deny"
        Action = [
          "elasticfilesystem:DeleteFileSystem",
          "elasticfilesystem:DeleteMountTarget",
          "elasticfilesystem:DeleteAccessPoint"
        ]
        Resource = "*"
      }
    ]
  })
}

# CloudWatch logs policy for task role with explicit deny
resource "aws_iam_role_policy" "ecs_task_cloudwatch" {
  name = "vimbiso-pay-ecs-task-cloudwatch-${var.environment}"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = [
          "${var.cloudwatch_log_group_arn}:*"
        ]
      },
      {
        Effect = "Deny"
        Action = [
          "logs:DeleteLogGroup",
          "logs:DeleteLogStream",
          "logs:DeleteMetricFilter",
          "logs:DeleteRetentionPolicy"
        ]
        Resource = "*"
      }
    ]
  })
}

# Additional permissions for task execution role (for SSM parameters and ECR)
resource "aws_iam_role_policy" "ecs_execution_extra" {
  name = "vimbiso-pay-ecs-execution-extra-${var.environment}"
  role = aws_iam_role.ecs_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage"
        ]
        Resource = "*"
        Condition = {
          StringLike = {
            "ecr:ResourceTag/Environment": var.environment
          }
        }
      },
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParameters",
          "ssm:GetParameter"
        ]
        Resource = [
          "arn:aws:ssm:${var.region}:${var.account_id}:parameter/vimbiso-pay/${var.environment}/*"
        ]
      },
      {
        Effect = "Deny"
        Action = [
          "ssm:DeleteParameter",
          "ssm:DeleteParameters",
          "ssm:PutParameter"
        ]
        Resource = "*"
      }
    ]
  })
}

# Service-linked role for ECS
resource "aws_iam_service_linked_role" "ecs" {
  aws_service_name = "ecs.amazonaws.com"
  description      = "Service-linked role for ECS"

  tags = merge(var.tags, {
    Name = "vimbiso-pay-ecs-service-linked-${var.environment}"
  })
}

# KMS key policy for encryption
resource "aws_iam_role_policy" "kms" {
  name = "vimbiso-pay-kms-${var.environment}"
  role = aws_iam_role.ecs_task_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "kms:ViaService": [
              "ecs.${var.region}.amazonaws.com",
              "ssm.${var.region}.amazonaws.com"
            ]
          }
        }
      }
    ]
  })
}
