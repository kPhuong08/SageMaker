# Variables for CloudWatch Monitoring Module

variable "endpoint_name" {
  description = "Name of the SageMaker endpoint to monitor"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "production"
}

variable "alert_email" {
  description = "Email address for alarm notifications (leave empty to skip email subscription)"
  type        = string
  default     = ""
}

variable "error_rate_threshold" {
  description = "Threshold for 5XX error count alarm"
  type        = number
  default     = 5
}

variable "latency_threshold_ms" {
  description = "Threshold for P99 latency alarm in milliseconds"
  type        = number
  default     = 3000
}

variable "training_lambda_function_name" {
  description = "Name of the training orchestrator Lambda function to monitor"
  type        = string
  default     = ""
}

variable "model_evaluator_lambda_function_name" {
  description = "Name of the model evaluator Lambda function to monitor"
  type        = string
  default     = ""
}

variable "deployment_lambda_function_name" {
  description = "Name of the deployment orchestrator Lambda function to monitor"
  type        = string
  default     = ""
}
