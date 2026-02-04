provider "aws" {
  region = "us-east-1"
}
variable "project_bucket_name" {
  description = "The name of the S3 bucket"
  type        = string
}