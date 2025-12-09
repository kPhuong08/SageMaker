variable "bucket_name" {
  description = "S3 bucket name for model artifacts"
  type        = string
  default     = ""
}

variable "create_bucket" {
  description = "Whether to create the bucket"
  type        = bool
  default     = true
}

variable "existing_bucket_name" {
  description = "Existing bucket name if not creating one"
  type        = string
  default     = ""
}
