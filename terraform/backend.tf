terraform {
  backend "s3" {
    region = "af-south-1"
    encrypt = true
    key    = "terraform.tfstate"
  }
}
