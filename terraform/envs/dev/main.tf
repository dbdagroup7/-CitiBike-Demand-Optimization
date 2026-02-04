# 1. S3
module "s3" {
  source      = "../../modules/s3"
  bucket_name = var.project_bucket_name # <--- This tells it to look at terraform.tfvars
}
import {
  to = module.s3.aws_s3_bucket.datalake
  id = "citibike-data-lake-group7"
}
# 2. IAM
module "iam" {
  source      = "../../modules/iam"
  bucket_name = module.s3.bucket_name
}

# 3. EC2 (For Ingestion)
#module "ec2" {
#  source               = "../../modules/ec2"
#  iam_instance_profile = module.iam.ec2_profile_name
#}

# 4. Athena
module "athena" {
  source      = "../../modules/athena"
  bucket_name = module.s3.bucket_name
}

# 5. Glue
module "glue" {
  source         = "../../modules/glue"
  bucket_name    = module.s3.bucket_name
  glue_role_arn  = module.iam.glue_role_arn
  athena_db_name = module.athena.database_name
  project_name   = var.project_name
  environment    = var.environment
}

# 6. EventBridge
module "eventbridge" {
  source               = "../../modules/eventbridge"
  bucket_name          = module.s3.bucket_name
  eventbridge_role_arn = module.iam.eventbridge_role_arn
  # We construct the ARN manually because the module output might be just the name
  glue_workflow_arn    = "arn:aws:glue:us-east-1:${data.aws_caller_identity.current.account_id}:workflow/${module.glue.workflow_name}"
  project_name         = var.project_name
}

data "aws_caller_identity" "current" {}