########################################
# GitHub OIDC Provider
########################################
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1"
  ]
}

locals {
  github_repo_full = "${var.github_org}/${var.github_repo}"
}

########################################
# GitHub OIDC Assume Role Policy
########################################
data "aws_iam_policy_document" "github_assume_role" {
  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values = [
        "repo:${local.github_repo_full}:environment:dev",
        "repo:${local.github_repo_full}:environment:test",
        "repo:${local.github_repo_full}:environment:prod"
      ]
    }
  }
}

########################################
# Deploy Glue Scripts Role (S3 access)
########################################
resource "aws_iam_role" "github_deploy_glue" {
  name               = "${var.project_name}-${var.environment}-github-deploy-glue"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json
}

data "aws_iam_policy_document" "github_deploy_glue_policy" {
  statement {
    effect = "Allow"
    actions = [
      "s3:ListBucket",
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject"
    ]
    resources = [
      "arn:aws:s3:::${var.s3_bucket_name}",
      "arn:aws:s3:::${var.s3_bucket_name}/*"
    ]
  }

  statement {
    effect = "Allow"
    actions = [
      "sts:GetCallerIdentity"
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "github_deploy_glue_inline" {
  name   = "${var.project_name}-${var.environment}-github-deploy-glue"
  role   = aws_iam_role.github_deploy_glue.id
  policy = data.aws_iam_policy_document.github_deploy_glue_policy.json
}

########################################
# Terraform Apply Role (Admin)
########################################
resource "aws_iam_role" "github_terraform" {
  name               = "${var.project_name}-${var.environment}-github-terraform"
  assume_role_policy = data.aws_iam_policy_document.github_assume_role.json
}

resource "aws_iam_role_policy_attachment" "github_terraform_admin" {
  role       = aws_iam_role.github_terraform.name
  policy_arn = "arn:aws:iam::aws:policy/AdministratorAccess"
}
