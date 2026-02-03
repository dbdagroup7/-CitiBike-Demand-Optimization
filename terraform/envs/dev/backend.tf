terraform {
  backend "s3" {
    bucket         = "ci-cd-testing-citibike-7"
    key            = "terraform/state/dev.tfstate"
    region         = "eu-north-1"
    dynamodb_table = null
  }
}
