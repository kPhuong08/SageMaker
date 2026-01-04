# Lambda function for redeploying SageMaker endpoint when new model is uploaded

resource "aws_lambda_function" "redeploy" {
  filename         = var.lambda_zip_path
  function_name    = "mlops-redeploy-${replace(var.bucket_name, "[^a-zA-Z0-9_-]", "-")}" 
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  handler          = var.lambda_handler
  runtime          = "python3.9"
  role             = var.lambda_role_arn
  timeout          = 300

  environment {
    variables = {
      BUCKET_NAME                 = var.bucket_name
      SAGEMAKER_ROLE_ARN          = var.sagemaker_role_arn
      ENDPOINT_NAME               = var.endpoint_name
      REGION                      = var.region
      SERVERLESS_MEMORY_MB        = tostring(var.serverless_memory_mb)
      SERVERLESS_MAX_CONCURRENCY  = tostring(var.serverless_max_concurrency)
      INFERENCE_IMAGE             = var.inference_image
      # Legacy variables (not used but kept for backward compatibility)
      INSTANCE_TYPE               = var.instance_type
      INSTANCE_COUNT              = tostring(var.instance_count)
    }
  }

  tags = {
    Name        = "MLOps Redeploy Endpoint"
    Environment = "production"
  }
}

# Permission for S3 to invoke Lambda
resource "aws_lambda_permission" "allow_s3" {
  count         = var.trigger_type == "s3" ? 1 : 0
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redeploy.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.bucket_arn
}

# Note: EventBridge Lambda permission is created in the eventbridge module
# to avoid duplication and ensure it references the correct source ARN.
