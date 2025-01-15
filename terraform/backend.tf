terraform {
  backend "s3" {
    region         = "af-south-1"
    encrypt        = true
    key            = "terraform.tfstate"
    # Bucket and DynamoDB table names are set via backend-config during terraform init:
    # development:    vimbiso-chatserver-terraform-state-development-195275664440 / vimbiso-chatserver-terraform-state-lock-development-195275664440
    # production: vimbiso-chatserver-terraform-state-production-195275664440 / vimbiso-chatserver-terraform-state-lock-production-195275664440
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
