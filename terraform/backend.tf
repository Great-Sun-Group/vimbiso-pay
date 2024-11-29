terraform {
  backend "s3" {
    region         = "af-south-1"
    encrypt        = true
    key            = "terraform.tfstate"
    # Bucket and DynamoDB table names are set via backend-config during terraform init:
    # staging:    vimbiso-pay-terraform-state-staging / vimbiso-pay-terraform-state-lock-staging
    # production: vimbiso-pay-terraform-state-production / vimbiso-pay-terraform-state-lock-production

    # Enable versioning
    versioning     = true
    # Enable server-side encryption
    sse_algorithm  = "AES256"
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

# Get current AWS account ID
data "aws_caller_identity" "current" {}
