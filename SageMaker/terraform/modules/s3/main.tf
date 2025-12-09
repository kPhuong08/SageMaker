resource "aws_s3_bucket" "models" {
  count  = var.create_bucket ? 1 : 0
  bucket = var.bucket_name

  versioning {
    enabled = true
  }

  tags = {
    Name = "ml-models-bucket"
  }
}
resource "aws_s3_bucket" "models" {
  count  = var.create_bucket ? 1 : 0
  bucket = var.bucket_name

  versioning {
    enabled = true
  }

  tags = {
    Name = "ml-models-bucket"
  }
}
