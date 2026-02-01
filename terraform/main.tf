terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "CitiBike-Demand-Optimization"
      ManagedBy   = "Terraform"
      Environment = var.environment
      Owner       = "SagarNikam"
      CreatedBy   = "Terraform"
    }
  }
}

# Data source to get current AWS account ID and region
data "aws_caller_identity" "current" {}

data "aws_region" "current" {}

