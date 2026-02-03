resource "aws_glue_crawler" "gold_crawler" {
  name          = "${var.project_name}-gold-crawler"
  role          = var.glue_role_arn
  database_name = "${var.project_name}_gold"

  s3_target {
    path = "s3://${var.bucket_name}/data/gold/"
  }
}
