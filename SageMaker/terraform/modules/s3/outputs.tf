output "s3_bucket_name" {
  value = aws_s3_bucket.models[0].bucket
  description = "Name of the S3 bucket created or referenced"
}
