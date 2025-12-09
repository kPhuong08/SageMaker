variable "endpoint_name" {
  description = "SageMaker endpoint name"
  type        = string
}

variable "instance_type" {
  description = "SageMaker instance type to use for the endpoint (if using provisioned instances)"
  type        = string
  default     = "ml.m5.large"
}

variable "instance_count" {
  description = "Number of instances for the endpoint"
  type        = number
  default     = 1
}
variable "endpoint_name" {
  description = "SageMaker endpoint name"
  type        = string
}

variable "instance_type" {
  description = "SageMaker instance type to use for the endpoint (if using provisioned instances)"
  type        = string
  default     = "ml.m5.large"
}