output "s3_bucket_name" {
  value = var.create_bucket ? aws_s3_bucket.models[0].bucket : var.existing_bucket_name
  description = "Name of the S3 bucket created or referenced"
}
