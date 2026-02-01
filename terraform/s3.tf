resource "aws_s3_object" "folders" {
  for_each = toset([
    "data/raw/",
    "data/silver/",
    "data/gold/",
    "glue_scripts/",
    "logs/",
    "temp/",
    "athena-results/"
  ])

  bucket = var.s3_bucket_name
  key    = each.value
}
