variable "bucket_name" {}
variable "glue_role_arn" {}
variable "athena_db_name" {}
variable "project_name" {
  description = "Project identifier for naming resources"
  type        = string
}

variable "environment" {
  description = "Environment name (e.g., dev, prod)"
  type        = string
}