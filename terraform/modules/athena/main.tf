resource "aws_glue_catalog_database" "db" {
  name = "citibike_analytics_db"
}

resource "aws_athena_workgroup" "bi_workgroup" {
  name = "powerbi_workgroup"
  configuration {
    result_configuration {
      output_location = "s3://${var.bucket_name}/athena-results/"
    }
  }
}

output "database_name" { value = aws_glue_catalog_database.db.name }