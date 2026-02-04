output "event_rule_name" {
  # Change "s3_trigger" to "s3_upload"
  value = aws_cloudwatch_event_rule.s3_upload.name 
}