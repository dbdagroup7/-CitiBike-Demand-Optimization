# ===================================
# GLUE WORKFLOW
# ===================================
resource "aws_glue_workflow" "citibike_wf" {
  name        = "${var.project_name}_pipeline"
  description = "Bronze -> Silver -> Gold medallion architecture"
  
  # Optional: Add max concurrent runs
  max_concurrent_runs = 1  # Prevent overlapping runs
}

# ===================================
# GLUE JOBS
# ===================================
resource "aws_glue_job" "job1" {
  name         = "${var.project_name}_raw_to_silver"
  role_arn     = var.glue_role_arn
  glue_version = "4.0"
  
  # Worker configuration
  worker_type       = "G.1X"  # 4 vCPU, 16 GB memory
  number_of_workers = 2       # Scale based on data volume
  
  # Timeout and retries
  timeout           = 60      # minutes
  max_retries       = 1
  
  command {
    name            = "glueetl"
    script_location = "s3://${var.bucket_name}/glue_scripts/raw_to_silver.py"
    python_version  = "3"
  }
  
  # Best Practice: Enable job bookmarks for incremental processing
  default_arguments = {
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "true"
    "--enable-spark-ui"                  = "true"
    "--spark-event-logs-path"            = "s3://${var.bucket_name}/spark-logs/"
    
    # Pass bucket as parameter for script reusability
    "--BUCKET" = var.bucket_name
  }
  
  tags = {
    Environment = var.environment
    Layer       = "Bronze-to-Silver"
  }
}

resource "aws_glue_job" "job2" {
  name         = "${var.project_name}_silver_to_gold"
  role_arn     = var.glue_role_arn
  glue_version = "4.0"
  
  worker_type       = "G.1X"
  number_of_workers = 2
  timeout           = 60
  max_retries       = 1
  
  command {
    name            = "glueetl"
    script_location = "s3://${var.bucket_name}/glue_scripts/silver_to_gold.py"
    python_version  = "3"
  }
  
  default_arguments = {
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-metrics"                   = "true"
    "--BUCKET"                           = var.bucket_name
    "--YEAR"                             = "2024"
  }
  
  tags = {
    Environment = var.environment
    Layer       = "Silver-to-Gold"
  }
}

# ===================================
# GLUE CRAWLER
# ===================================
resource "aws_glue_crawler" "gold_crawler" {
  name          = "${var.project_name}_gold_crawler"
  role          = var.glue_role_arn
  database_name = var.athena_db_name
  
  # Crawl strategy
  schedule = null  # Only run via workflow trigger
  
  # Target both dimensions and facts
  s3_target {
    path = "s3://${var.bucket_name}/data/gold/dimensions/"
  }
  
  s3_target {
    path = "s3://${var.bucket_name}/data/gold/facts/"
  }
  
  # Schema change handling
  schema_change_policy {
    delete_behavior = "DEPRECATE_IN_DATABASE" # or "LOG"
    update_behavior = "UPDATE_IN_DATABASE"    # Now allowed!
  }
  
  
  tags = {
    Environment = var.environment
    Layer       = "Gold"
  }
}

# ===================================
# WORKFLOW TRIGGERS
# ===================================

# Trigger 1: Start Job 1 (EventBridge → Workflow)
resource "aws_glue_trigger" "start_trigger" {
  name          = "${var.project_name}_start_workflow"
  type          = "ON_DEMAND"  # Called by EventBridge
  workflow_name = aws_glue_workflow.citibike_wf.name
  
  actions {
    job_name = aws_glue_job.job1.name
  }
  
  # Optional: Batch events before triggering
  # event_batching_condition {
  #   batch_size   = 3    # Wait for 3 files
  #   batch_window = 300  # Or 5 minutes, whichever comes first
  # }
}

# Trigger 2: Job1 Success → Start Job2
resource "aws_glue_trigger" "job1_to_job2" {
  name          = "${var.project_name}_silver_trigger"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.citibike_wf.name
  
  predicate {
    conditions {
      job_name = aws_glue_job.job1.name
      state    = "SUCCEEDED"  # Only run if Job1 succeeds
    }
  }
  
  actions {
    job_name = aws_glue_job.job2.name
  }
}

# Trigger 3: Job2 Success → Start Crawler
resource "aws_glue_trigger" "job2_to_crawler" {
  name          = "${var.project_name}_gold_crawler_trigger"
  type          = "CONDITIONAL"
  workflow_name = aws_glue_workflow.citibike_wf.name
  
  predicate {
    conditions {
      job_name = aws_glue_job.job2.name
      state    = "SUCCEEDED"
    }
  }
  
  actions {
    crawler_name = aws_glue_crawler.gold_crawler.name
  }
}

# ===================================
# OUTPUTS
# ===================================
output "workflow_name" {
  description = "Workflow name for EventBridge target"
  value       = aws_glue_workflow.citibike_wf.name
}

output "workflow_arn" {
  description = "Workflow ARN for IAM policies"
  value       = aws_glue_workflow.citibike_wf.arn
}

output "job1_name" {
  value = aws_glue_job.job1.name
}

output "job2_name" {
  value = aws_glue_job.job2.name
}

output "crawler_name" {
  value = aws_glue_crawler.gold_crawler.name
}
