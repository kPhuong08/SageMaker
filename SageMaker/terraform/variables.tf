variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "S3 bucket name to create/use for model artifacts"
  type        = string
  default     = "my-ml-models-bucket-12345"
}

variable "create_bucket" {
  description = "Whether to create the S3 bucket"
  type        = bool
  default     = true
}

variable "existing_bucket_name" {
  description = "Name of an existing bucket to use when create_bucket=false"
  type        = string
  default     = ""
}

variable "lambda_zip_path" {
  description = "Path to the packaged Lambda zip"
  type        = string
  default     = "${path.module}/../lambda/redeploy_endpoint/redeploy.zip"
}

variable "lambda_handler" {
  description = "Lambda handler"
  type        = string
  default     = "handler.lambda_handler"
}

variable "endpoint_name" {
  description = "SageMaker endpoint name"
  type        = string
  default     = "hf-inference-endpoint"
}

variable "trigger_type" {
  description = "Trigger type: 's3' or 'eventbridge'"
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
  description = "Optional inference container image URI"
  type        = string
  default     = ""
}
