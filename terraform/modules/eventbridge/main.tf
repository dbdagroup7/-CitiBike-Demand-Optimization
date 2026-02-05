resource "aws_cloudwatch_event_rule" "s3_upload" {
  name        = "citibike_s3_trigger"
  description = "Trigger Glue when data lands in raw/"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = { name = [var.bucket_name] }
      object = { key = [{ prefix = "data/raw/citibike/" }] }
    }
  })
}

resource "aws_cloudwatch_event_target" "glue" {
  rule      = aws_cloudwatch_event_rule.s3_upload.name
  target_id = "TriggerGlueWorkflow"
  arn       = var.glue_workflow_arn
  role_arn  = var.eventbridge_role_arn
}