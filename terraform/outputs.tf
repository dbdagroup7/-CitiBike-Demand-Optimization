output "s3_bucket_name" {
  value       = var.s3_bucket_name
  description = "Data lake bucket"
}

output "workflow_name" {
  value       = aws_glue_workflow.citibike_etl.name
  description = "Glue ETL workflow name"
}

output "raw_data_path" {
  value       = "s3://${var.s3_bucket_name}/data/raw/citibike/"
  description = "Upload CitiBike CSVs here to trigger ETL"
}

output "silver_data_path" {
  value = "s3://${var.s3_bucket_name}/data/silver/citibike/"
}

output "gold_data_path" {
  value = "s3://${var.s3_bucket_name}/data/gold/citibike/"
}

output "github_deploy_glue_role_arn" {
  description = "IAM role ARN for GitHub Actions to deploy Glue scripts"
  value       = aws_iam_role.github_deploy_glue.arn
}

output "github_terraform_role_arn" {
  description = "IAM role ARN for GitHub Actions to run Terraform"
  value       = aws_iam_role.github_terraform.arn
}
