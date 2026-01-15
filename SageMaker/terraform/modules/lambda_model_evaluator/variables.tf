variable "lambda_zip_path" {
  description = "Path to the Lambda deployment package"
  type        = string
}

variable "lambda_handler" {
  description = "Lambda function handler"
  type        = string
  default     = "handler.lambda_handler"
}

variable "bucket_name" {
  description = "Name of the S3 bucket for ML models"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of the IAM role for Lambda execution"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  type        = string
}
