module "iam" {
  source       = "../../modules/iam"
  project_name = var.project_name
  bucket_name  = var.bucket_name
}

module "glue" {
  source          = "../../modules/glue"
  project_name    = var.project_name
  bucket_name     = var.bucket_name
  glue_role_arn  = module.iam.glue_role_arn
}

module "eventbridge" {
  source         = "../../modules/eventbridge"
  project_name   = var.project_name
  glue_job_name  = module.glue.job1_name
}
