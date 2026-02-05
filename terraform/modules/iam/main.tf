# --- GLUE ROLE ---
resource "aws_iam_role" "glue_service_role" {
  name = "citibike_glue_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "glue.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "glue_managed" {
  role       = aws_iam_role.glue_service_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

resource "aws_iam_role_policy" "s3_access_glue" {
  name = "glue_s3_access"
  role = aws_iam_role.glue_service_role.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"],
      Resource = ["arn:aws:s3:::${var.bucket_name}", "arn:aws:s3:::${var.bucket_name}/*"]
    }]
  })
}

# --- EC2 ROLE (For Ingestion) ---
resource "aws_iam_role" "ec2_ingestion_role" {
  name = "citibike_ec2_ingestion_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "ec2_s3_upload" {
  name = "ec2_s3_upload_policy"
  role = aws_iam_role.ec2_ingestion_role.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{
      Effect = "Allow", Action = ["s3:PutObject", "s3:ListBucket"],
      Resource = ["arn:aws:s3:::${var.bucket_name}", "arn:aws:s3:::${var.bucket_name}/raw/*"]
    }]
  })
}

resource "aws_iam_instance_profile" "ec2_profile" {
  name = "citibike_ec2_profile"
  role = aws_iam_role.ec2_ingestion_role.name
}

# --- EVENTBRIDGE ROLE ---
resource "aws_iam_role" "eventbridge_glue_role" {
  name = "eb_invoke_glue_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Action = "sts:AssumeRole", Effect = "Allow", Principal = { Service = "events.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "eb_invoke_glue" {
  name = "eb_invoke_glue_policy"
  role = aws_iam_role.eventbridge_glue_role.id
  policy = jsonencode({
    Version = "2012-10-17", Statement = [{ Effect = "Allow", Action = ["glue:notifyEvent","glue:StartWorkflowRun" ], Resource = "*" }]
  })
}

output "glue_role_arn" { value = aws_iam_role.glue_service_role.arn }
output "ec2_profile_name" { value = aws_iam_instance_profile.ec2_profile.name }
output "eventbridge_role_arn" { value = aws_iam_role.eventbridge_glue_role.arn }