variable "lambda_zip_path" {
  description = "Local path to the Lambda zip file (relative to root of Terraform execution)"
  type        = string
}

variable "lambda_handler" {
  description = "Lambda handler (module.function)"
  type        = string
  default     = "handler.lambda_handler"
}

variable "bucket_name" {
  description = "S3 bucket name"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of the IAM role to use for the Lambda function"
  type        = string
}

variable "github_token" {
  description = "GitHub personal access token for triggering workflows"
  type        = string
  sensitive   = true
}

variable "github_owner" {
  description = "GitHub repository owner/organization"
  type        = string
}

variable "github_repo" {
  description = "GitHub repository name"
  type        = string
}

variable "workflow_id" {
  description = "GitHub workflow file name"
  type        = string
  default     = "mlops.yml"
}