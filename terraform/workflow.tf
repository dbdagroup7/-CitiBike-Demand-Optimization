########################################
# Glue Workflow
########################################
resource "aws_glue_workflow" "citibike_etl" {
  name        = "${var.project_name}-${var.environment}-etl-workflow"
  description = "S3 Upload → Job1 → Job2 → Crawlers"

  tags = {
    Name        = "CitiBike ETL Workflow"
    Environment = var.environment
  }
}

########################################
# EventBridge: S3 ObjectCreated → Workflow
########################################
resource "aws_cloudwatch_event_rule" "s3_upload_trigger" {
  name        = "${var.project_name}-${var.environment}-s3-upload-trigger"
  description = "Trigger Glue workflow on raw CitiBike upload"

  event_pattern = jsonencode({
    source        = ["aws.s3"]
    "detail-type" = ["Object Created"]
    detail = {
      bucket = {
        name = [var.s3_bucket_name]
      }
      object = {
        key = [{
          prefix = "data/raw/citibike/"
        }]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "start_workflow" {
  rule     = aws_cloudwatch_event_rule.s3_upload_trigger.name
  arn      = "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:workflow/${aws_glue_workflow.citibike_etl.name}"
  role_arn = aws_iam_role.eventbridge_glue_role.arn
}

########################################
# Trigger 1: START (ON_DEMAND) → Job1
########################################
resource "aws_glue_trigger" "start_job1" {
  name          = "${var.project_name}-${var.environment}-start-job1"
  type          = "ON_DEMAND"
  workflow_name = aws_glue_workflow.citibike_etl.name
  enabled       = true

  actions {
    job_name = aws_glue_job.job1_bronze_to_silver.name
  }
}

########################################
# Trigger 2: Job1 SUCCESS → Job2
########################################
resource "aws_glue_trigger" "job1_to_job2" {
  name          = "${var.project_name}-${var.environment}-job1-to-job2"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.citibike_etl.name
  enabled       = true

  predicate {
    conditions {
      job_name = aws_glue_job.job1_bronze_to_silver.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    job_name = aws_glue_job.job2_silver_to_gold.name
  }
}

########################################
# Trigger 3a: Job1 SUCCESS → Raw + Silver Crawlers
########################################
resource "aws_glue_trigger" "job1_to_raw_silver_crawlers" {
  name          = "${var.project_name}-${var.environment}-job1-to-raw-silver-crawlers"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.citibike_etl.name
  enabled       = true

  predicate {
    conditions {
      job_name = aws_glue_job.job1_bronze_to_silver.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    crawler_name = aws_glue_crawler.raw_data_crawler.name
  }

  actions {
    crawler_name = aws_glue_crawler.silver_crawler.name
  }
}

########################################
# Trigger 3b: Job1 SUCCESS → Gold Crawler
########################################
resource "aws_glue_trigger" "job1_to_gold_crawler" {
  name          = "${var.project_name}-${var.environment}-job1-to-gold-crawler"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.citibike_etl.name
  enabled       = true

  predicate {
    conditions {
      job_name = aws_glue_job.job1_bronze_to_silver.name
      state    = "SUCCEEDED"
    }
  }

  actions {
    crawler_name = aws_glue_crawler.gold_crawler.name
  }
}
