terraform {
  backend "s3" {
    bucket         = "citibike-data-lake-group7"
    key            = "terraform/state/dev.tfstate"
    region         = "us-east-1"
    dynamodb_table = null
  }
}
