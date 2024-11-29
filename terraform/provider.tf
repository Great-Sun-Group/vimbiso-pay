provider "aws" {
  region = "af-south-1"

  default_tags {
    tags = local.common_tags
  }
}
