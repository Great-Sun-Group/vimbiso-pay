terraform {
  backend "s3" {
    region         = "af-south-1"
    encrypt        = true
    key            = "terraform.tfstate"
    # Bucket and DynamoDB table names are set via backend-config during terraform init:
    # staging:    vimbiso-pay-terraform-state-staging-195275664440 / vimbiso-pay-terraform-state-lock-staging-195275664440
    # production: vimbiso-pay-terraform-state-production-195275664440 / vimbiso-pay-terraform-state-lock-production-195275664440
  }

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.0"
    }
  }
}

# Get current AWS account ID
data "aws_caller_identity" "current" {}
