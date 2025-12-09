variable "bucket_name" {
  description = "S3 bucket name"
  type        = string
}

variable "bucket_arn" {
  description = "S3 bucket arn"
  type        = string
  default     = ""
}

variable "create_bucket" {
  description = "Whether the bucket is created by the s3 module"
  type        = bool
  default     = true
}
