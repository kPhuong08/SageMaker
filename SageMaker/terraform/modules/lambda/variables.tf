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

variable "bucket_arn" {
  description = "S3 bucket arn"
  type        = string
}

variable "lambda_role_arn" {
  description = "ARN of the IAM role to use for the Lambda function"
  type        = string
}

variable "sagemaker_role_arn" {
  description = "ARN of the SageMaker execution role"
  type        = string
}

variable "endpoint_name" {
  description = "SageMaker endpoint name"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "trigger_type" {
  description = "Trigger mechanism for new model artifacts. 's3' or 'eventbridge'"
  type        = string
  default     = "s3"
}

# Serverless configuration
variable "serverless_memory_mb" {
  description = "Memory size for serverless endpoint in MB"
  type        = number
  default     = 4096
}

variable "serverless_max_concurrency" {
  description = "Maximum concurrent invocations for serverless endpoint"
  type        = number
  default     = 10
}

# Legacy variables (deprecated, kept for backward compatibility)
variable "instance_type" {
  description = "[DEPRECATED] SageMaker instance type - not used with serverless"
  type        = string
  default     = "ml.m5.large"
}

variable "instance_count" {
  description = "[DEPRECATED] SageMaker instance count - not used with serverless"
  type        = number
  default     = 1
}

variable "inference_image" {
  description = "Inference container image override"
  type        = string
  default     = ""
}
