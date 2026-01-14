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

# Enable S3 event notifications to EventBridge
resource "aws_s3_bucket_notification" "models_notification" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id

  eventbridge = true
}

# Create folder structure in S3 bucket
# S3 doesn't have real folders, but we create placeholder objects to establish the structure
resource "aws_s3_object" "data_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "data/"
  content = ""
  content_type = "application/x-directory"
}

resource "aws_s3_object" "data_train_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "data/train/"
  content = ""
  content_type = "application/x-directory"
}

resource "aws_s3_object" "data_validation_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "data/validation/"
  content = ""
  content_type = "application/x-directory"
}

resource "aws_s3_object" "data_test_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "data/test/"
  content = ""
  content_type = "application/x-directory"
}

resource "aws_s3_object" "models_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "models/"
  content = ""
  content_type = "application/x-directory"
}

resource "aws_s3_object" "models_raw_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "models/raw/"
  content = ""
  content_type = "application/x-directory"
}

resource "aws_s3_object" "models_approved_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "models/approved/"
  content = ""
  content_type = "application/x-directory"
}

resource "aws_s3_object" "models_code_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "models/code/"
  content = ""
  content_type = "application/x-directory"
}

resource "aws_s3_object" "config_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "config/"
  content = ""
  content_type = "application/x-directory"
}

# Upload evaluation thresholds config file
resource "aws_s3_object" "evaluation_thresholds" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "config/evaluation_thresholds.json"
  source = "${path.module}/../../../config/evaluation_thresholds.json"
  etag   = filemd5("${path.module}/../../../config/evaluation_thresholds.json")
  
  content_type = "application/json"
  
  tags = {
    Name        = "Evaluation Thresholds"
    Description = "Model quality thresholds for automatic approval"
  }
}

resource "aws_s3_object" "logs_folder" {
  count  = var.create_bucket ? 1 : 0
  bucket = aws_s3_bucket.models[0].id
  key    = "logs/"
  content = ""
  content_type = "application/x-directory"
}
