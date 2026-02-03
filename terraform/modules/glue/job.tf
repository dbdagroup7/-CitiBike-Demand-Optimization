resource "aws_glue_job" "job1" {
  name     = "${var.project_name}-raw-to-silver"
  role_arn = var.glue_role_arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.bucket_name}/glue_scripts/raw_to_silver.py"
    python_version  = "3"
  }

  glue_version = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"
}

resource "aws_glue_job" "job2" {
  name     = "${var.project_name}-silver-to-gold"
  role_arn = var.glue_role_arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.bucket_name}/glue_scripts/silver_to_gold.py"
    python_version  = "3"
  }

  glue_version = "4.0"
  number_of_workers = 2
  worker_type       = "G.1X"
}
