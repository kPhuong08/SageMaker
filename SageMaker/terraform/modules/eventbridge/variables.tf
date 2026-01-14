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

variable "training_orchestrator_lambda_arn" {
  description = "ARN of the Training Orchestrator Lambda function"
  type        = string
}

variable "training_orchestrator_lambda_name" {
  description = "Name of the Training Orchestrator Lambda function (used for permissions)"
  type        = string
}

variable "deployment_orchestrator_lambda_arn" {
  description = "ARN of the Deployment Orchestrator Lambda function"
  type        = string
}

variable "deployment_orchestrator_lambda_name" {
  description = "Name of the Deployment Orchestrator Lambda function (used for permissions)"
  type        = string
}
