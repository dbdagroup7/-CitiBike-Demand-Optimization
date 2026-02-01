variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1" # ← CHANGE if you use another region
}

variable "project_name" {
  description = "Short project prefix"
  type        = string
  default     = "citibike" # ← CHANGE if you prefer a different prefix
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "test" # ← CHANGE to dev / prod etc.
}

variable "s3_bucket_name" {
  description = "Existing S3 bucket for data lake"
  type        = string
  default     = "ci-cd-testing-citibike-7" # ← CHANGE to your bucket
}
