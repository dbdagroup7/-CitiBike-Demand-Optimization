resource "aws_athena_database" "this" {
  name   = "citibike_gold"
  bucket = var.bucket_name
}
