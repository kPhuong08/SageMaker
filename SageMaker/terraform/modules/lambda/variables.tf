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

variable "instance_type" {
  description = "SageMaker instance type"
  type        = string
  default     = "ml.m5.large"
}

variable "instance_count" {
  description = "SageMaker instance count"
  type        = number
  default     = 1
}

variable "inference_image" {
  description = "Inference container image override"
  type        = string
  default     = ""
}
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

variable "bucket_create" {
  description = "Whether the bucket is created by s3 module"
  type        = bool
  default     = true
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

variable "instance_type" {
  description = "SageMaker instance type"
  type        = string
  default     = "ml.m5.large"
}

variable "instance_count" {
  description = "SageMaker instance count"
  type        = number
  default     = 1
}

variable "inference_image" {
  description = "Inference container image override"
  type        = string
  default     = ""
}

variable "lambda_zip_path" {
  description = "Local path to the Lambda zip file (relative to root of Terraform execution)"
  type        = string
}

variable "lambda_handler" {
  description = "Lambda handler (module.function)"
  type        = string
  default     = "handler.lambda_handler"
}
