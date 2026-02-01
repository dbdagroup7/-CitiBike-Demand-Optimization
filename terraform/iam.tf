# Glue service role (used by Glue jobs and crawlers)
resource "aws_iam_role" "glue_role" {
  name = "${var.project_name}-${var.environment}-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "glue.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

# Basic Glue permissions: S3 + CloudWatch Logs
resource "aws_iam_role_policy" "glue_s3" {
  name = "${var.project_name}-${var.environment}-glue-s3"
  role = aws_iam_role.glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# EventBridge → Glue workflow role
resource "aws_iam_role" "eventbridge_glue_role" {
  name = "${var.project_name}-${var.environment}-eventbridge-glue-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "eventbridge_start_workflow" {
  name = "${var.project_name}-${var.environment}-start-workflow-policy"
  role = aws_iam_role.eventbridge_glue_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "glue:StartWorkflowRun"
      Resource = "arn:aws:glue:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:workflow/${var.project_name}-${var.environment}-etl-workflow"
    }]
  })
}
