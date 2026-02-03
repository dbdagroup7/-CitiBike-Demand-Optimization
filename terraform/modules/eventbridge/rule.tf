resource "aws_cloudwatch_event_rule" "s3_trigger" {
  name = "${var.project_name}-s3-raw-trigger"

  event_pattern = jsonencode({
    source = ["aws.s3"]
    detail-type = ["Object Created"]
  })
}
