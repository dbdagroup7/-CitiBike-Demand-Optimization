variable "bucket_name" {}
variable "glue_workflow_arn" {}
variable "eventbridge_role_arn" {}
variable "project_name" {
  description = "Project identifier for naming resources"
  type        = string
}