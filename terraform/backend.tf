terraform {
  backend "s3" {
    region         = "af-south-1"
    encrypt        = true
    key            = "terraform.tfstate"
    # Bucket and DynamoDB table names are set via backend-config during terraform init:
    # staging:    vimbiso-pay-terraform-state-staging / vimbiso-pay-terraform-state-lock-staging
    # production: vimbiso-pay-terraform-state-production / vimbiso-pay-terraform-state-lock-production

    # Additional security configurations
    kms_key_id     = "alias/terraform-bucket-key"
    # Enable versioning
    versioning     = true
    # Enable server-side encryption
    sse_algorithm  = "aws:kms"
    # Enable access logging
    access_logging = true
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

provider "aws" {
  region = local.current_env.aws_region

  default_tags {
    tags = local.common_tags
  }

  # Enable AWS provider features
  assume_role {
    role_arn = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/terraform-execution"
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}
