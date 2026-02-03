resource "aws_sns_topic" "glue_failures" {
  name = "${var.project_name}-${var.environment}-glue-failures"
}

resource "aws_sns_topic_subscription" "alert_email" {
  count     = length(trimspace(var.alert_email)) > 0 ? 1 : 0
  topic_arn = aws_sns_topic.glue_failures.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_sns_topic_policy" "allow_eventbridge" {
  arn = aws_sns_topic.glue_failures.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.glue_failures.arn
    }]
  })
}

resource "aws_cloudwatch_event_rule" "glue_job_failure" {
  name        = "${var.project_name}-${var.environment}-glue-job-failure"
  description = "Notify on Glue job failures/timeouts"

  event_pattern = jsonencode({
    source        = ["aws.glue"]
    "detail-type" = ["Glue Job State Change"]
    detail = {
      state = ["FAILED", "TIMEOUT"]
      jobName = [
        aws_glue_job.job1_bronze_to_silver.name,
        aws_glue_job.job2_silver_to_gold.name
      ]
    }
  })
}

resource "aws_cloudwatch_event_target" "glue_job_failure_to_sns" {
  rule      = aws_cloudwatch_event_rule.glue_job_failure.name
  arn       = aws_sns_topic.glue_failures.arn
  target_id = "glue-job-failure-sns"
}
