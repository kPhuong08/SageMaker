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
  description = "S3 bucket name"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of the IAM role for Lambda execution"
  type        = string
}

variable "sagemaker_role_arn" {
  description = "ARN of the IAM role for SageMaker execution"
  type        = string
}

variable "endpoint_name" {
  description = "SageMaker endpoint name"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "serverless_memory_mb" {
  description = "Memory size for serverless endpoint"
  type        = number
  default     = 4096
}

variable "serverless_max_concurrency" {
  description = "Max concurrency for serverless endpoint"
  type        = number
  default     = 10
}

variable "inference_image" {
  description = "Docker image for inference"
  type        = string
}

variable "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  type        = string
}