variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "S3 bucket name to create/use for model artifacts"
  type        = string
  default     = "atml-models-bucket"
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

#variable "lambda_zip_path" {
#  description = "Path to the packaged Lambda zip"
#  type        = string
#  # default     = "${path.module}/../lambda/redeploy_endpoint/redeploy.zip"
#}

#variable "lambda_handler" {
#  description = "Lambda handler"
#  type        = string
#  default     = "handler.lambda_handler"
#}

#variable "source_file" {
#  description = "Path to the Lambda source file"
#  type        = string
#  default     = "/../lambda/redeploy_endpoint/handler.py"
#}

variable "endpoint_name" {
  description = "SageMaker endpoint name"
  type        = string
  default     = "serverless-inference-endpoint"
}

variable "trigger_type" {
  description = "[DEPRECATED] Trigger type - now always 'eventbridge' for event-driven architecture"
  type        = string
  default     = "eventbridge"
}

# Serverless Endpoint Configuration
variable "serverless_memory_mb" {
  description = "Memory size for serverless endpoint in MB (1024, 2048, 3072, 4096, 5120, 6144)"
  type        = number
  default     = 4096
  
  validation {
    condition     = contains([1024, 2048, 3072, 4096, 5120, 6144], var.serverless_memory_mb)
    error_message = "Memory size must be one of: 1024, 2048, 3072, 4096, 5120, 6144 MB"
  }
}

variable "serverless_max_concurrency" {
  description = "Maximum concurrent invocations for serverless endpoint (1-20)"
  type        = number
  default     = 10
  
  validation {
    condition     = var.serverless_max_concurrency >= 1 && var.serverless_max_concurrency <= 200
    error_message = "Max concurrency must be between 1 and 200"
  }
}

# Monitoring Configuration
variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "production"
}

variable "alert_email" {
  description = "Email address for CloudWatch alarm notifications (leave empty to skip)"
  type        = string
  default     = ""
}

variable "error_rate_threshold" {
  description = "Threshold for 5XX error count alarm"
  type        = number
  default     = 5
}

variable "latency_threshold_ms" {
  description = "Threshold for P99 latency alarm in milliseconds (serverless typically 1000-3000ms)"
  type        = number
  default     = 3000
}

# Legacy variables (kept for backward compatibility but not used with serverless)
variable "instance_type" {
  description = "[DEPRECATED] SageMaker instance type - not used with serverless endpoints"
  type        = string
  default     = "ml.m5.large"
}

variable "instance_count" {
  description = "[DEPRECATED] SageMaker instance count - not used with serverless endpoints"
  type        = number
  default     = 1
}

variable "inference_image" {
  description = "Optional inference container image URI"
  type        = string
  default     = ""
}
# Removed: GitHub workflow triggering variables - no longer needed for event-driven architecture

# Training Orchestrator Lambda Configuration
variable "training_orchestrator_source_file" {
  description = "Path to the training orchestrator Lambda source file"
  type        = string
  default     = "../lambda/training_orchestrator/handler.py"
}

variable "training_orchestrator_handler" {
  description = "Training orchestrator Lambda handler"
  type        = string
  default     = "handler.lambda_handler"
}

# Deployment Orchestrator Lambda Configuration
variable "deployment_orchestrator_source_file" {
  description = "Path to the deployment orchestrator Lambda source file"
  type        = string
  default     = "../lambda/deployment_orchestrator/handler.py"
}

variable "deployment_orchestrator_handler" {
  description = "Deployment orchestrator Lambda handler"
  type        = string
  default     = "handler.lambda_handler"
}