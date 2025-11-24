terraform {
  backend "s3" {
    bucket         = "brb-app-tf-state-2024"
    key            = "terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "brb-app-tf-locks"
    encrypt        = true
  }
}