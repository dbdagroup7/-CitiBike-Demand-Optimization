# Glue database
resource "aws_glue_catalog_database" "citibike_db" {
  name        = "${var.project_name}_${var.environment}_db"
  description = "CitiBike analytics database"
}
resource "aws_glue_job" "job1_bronze_to_silver" {
  name     = "${var.project_name}-${var.environment}-job1-bronze-to-silver"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${var.s3_bucket_name}/glue_scripts/latest/raw_to_silver.py"
  }

  glue_version      = "4.0"
  number_of_workers = 4
  worker_type       = "G.1X"
  timeout           = 60
  max_retries       = var.glue_max_retries

  execution_property {
    max_concurrent_runs = var.glue_max_concurrent_runs
  }

  default_arguments = {
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--TempDir"                          = "s3://${var.s3_bucket_name}/temp/"

    "--raw_path"      = "s3://${var.s3_bucket_name}/data/raw/citibike/"
    "--silver_path"   = "s3://${var.s3_bucket_name}/data/silver/citibike/"
    "--database_name" = aws_glue_catalog_database.citibike_db.name

    # 🔥 REQUIRED ARGUMENTS
    "--BUCKET" = var.s3_bucket_name
    "--YEAR"   = "2025"
  }
}

resource "aws_glue_job" "job2_silver_to_gold" {
  name     = "${var.project_name}-${var.environment}-job2-silver-to-gold"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    python_version  = "3"
    script_location = "s3://${var.s3_bucket_name}/glue_scripts/latest/silver_to_gold.py"
  }

  glue_version      = "4.0"
  number_of_workers = 4
  worker_type       = "G.1X"
  timeout           = 60
  max_retries       = var.glue_max_retries

  execution_property {
    max_concurrent_runs = var.glue_max_concurrent_runs
  }

  default_arguments = {
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-metrics"                   = "true"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-spark-ui"                  = "true"
    "--TempDir"                          = "s3://${var.s3_bucket_name}/temp/"

    "--silver_path"   = "s3://${var.s3_bucket_name}/data/silver/citibike/"
    "--gold_path"     = "s3://${var.s3_bucket_name}/data/gold/citibike/"
    "--database_name" = aws_glue_catalog_database.citibike_db.name

    # 🔥 REQUIRED ARGUMENTS
    "--BUCKET" = var.s3_bucket_name
    "--YEAR"   = "2025"
  }
}

# Crawlers
resource "aws_glue_crawler" "raw_data_crawler" {
  name          = "${var.project_name}-${var.environment}-raw-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.citibike_db.name

  s3_target {
    path = "s3://${var.s3_bucket_name}/data/raw/citibike/"
  }

  table_prefix = "raw_"
}

resource "aws_glue_crawler" "silver_crawler" {
  name          = "${var.project_name}-${var.environment}-silver-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.citibike_db.name

  s3_target {
    path = "s3://${var.s3_bucket_name}/data/silver/citibike/"
  }

  table_prefix = "silver_"
}

resource "aws_glue_crawler" "gold_crawler" {
  name          = "${var.project_name}-${var.environment}-gold-crawler"
  role          = aws_iam_role.glue_role.arn
  database_name = aws_glue_catalog_database.citibike_db.name

  s3_target {
    path = "s3://${var.s3_bucket_name}/data/gold/citibike/"
  }

  table_prefix = "gold_"
}
