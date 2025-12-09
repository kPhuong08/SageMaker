variable "bucket_name" {
  description = "S3 bucket name for model artifacts"
  type        = string
}

variable "create_bucket" {
  description = "Whether to create a new S3 bucket. If false, provide `existing_bucket_name`."
  type        = bool
  default     = true
}

variable "existing_bucket_name" {
  description = "Name of an existing S3 bucket to use when `create_bucket` is false"
  type        = string
  default     = ""
}

variable "trigger_type" {
  description = "Trigger mechanism for new model artifacts. 's3' or 'eventbridge'"
  type        = string
  default     = "s3"
}

variable "lambda_function_arn" {
  description = "ARN of the Lambda function to invoke"
  type        = string
}

variable "lambda_function_name" {
  description = "Name of the Lambda function (used for permissions)"
  type        = string
}
