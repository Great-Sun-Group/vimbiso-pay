terraform {
  backend "s3" {
    region = "af-south-1"
    encrypt = true
    key    = "terraform.tfstate"
    # Bucket and DynamoDB table names are set via backend-config during terraform init:
    # staging:    vimbiso-pay-terraform-state-staging / vimbiso-pay-terraform-state-lock-staging
    # production: vimbiso-pay-terraform-state-production / vimbiso-pay-terraform-state-lock-production
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
}
