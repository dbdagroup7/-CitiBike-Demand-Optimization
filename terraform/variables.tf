variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1" # â† CHANGE if you use another region
}

variable "project_name" {
  description = "Short project prefix"
  type        = string
  default     = "citibike" # â† CHANGE if you prefer a different prefix
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "test" # â† CHANGE to dev / prod etc.
}

variable "s3_bucket_name" {
  description = "Existing S3 bucket for data lake"
  type        = string
  default     = "ci-cd-testing-citibike-7" # â† CHANGE to your bucket
}

variable "glue_max_retries" {
  description = "Maximum retries for Glue jobs"
  type        = number
  default     = 1
}

variable "glue_max_concurrent_runs" {
  description = "Maximum concurrent runs for Glue jobs"
  type        = number
  default     = 1
}

variable "alert_email" {
  description = "Email address for failure notifications (leave blank to disable email subscription)"
  type        = string
  default     = ""
}
