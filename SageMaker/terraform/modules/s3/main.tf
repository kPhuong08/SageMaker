resource "aws_s3_bucket" "models" {
  count  = var.create_bucket ? 1 : 0
  bucket = var.bucket_name

  tags = {
    Name = "ml-models-bucket"
  }
}

resource "aws_s3_bucket_versioning" "models" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id

  versioning_configuration {
    status = "Enabled"
  }
}
