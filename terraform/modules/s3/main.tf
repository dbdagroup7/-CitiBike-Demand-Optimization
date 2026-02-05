resource "aws_s3_bucket" "datalake" {
  bucket        = var.bucket_name
  force_destroy = false  # CHANGED: Safety first! Prevents deletion if bucket has data.

  # NEW: This is the ultimate safety lock. 
  # Terraform will error and fail if anyone tries to destroy this bucket.
  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket      = aws_s3_bucket.datalake.id
  eventbridge = true
}

output "bucket_name" { value = aws_s3_bucket.datalake.id }
output "bucket_arn"  { value = aws_s3_bucket.datalake.arn }