resource "aws_s3_bucket" "datalake" {
  bucket = var.bucket_name
}

# Important: Turn on EventBridge notifications for this bucket
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket      = aws_s3_bucket.datalake.id
  eventbridge = true
}

output "bucket_name" {
  value = aws_s3_bucket.datalake.id
}