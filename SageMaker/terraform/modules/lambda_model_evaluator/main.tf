resource "aws_lambda_function" "model_evaluator" {
  filename        = var.lambda_zip_path
  function_name   = "mlops-model-evaluator-${var.bucket_name}"
  role            = var.lambda_role_arn
  handler         = var.lambda_handler
  runtime         = "python3.9"
  timeout         = 300  # 5 minutes for model evaluation
  memory_size     = 1024  # More memory for downloading and extracting model

  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      BUCKET_NAME   = var.bucket_name
      REGION        = var.region
      SNS_TOPIC_ARN = var.sns_topic_arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.model_evaluator_logs,
  ]
}

resource "aws_cloudwatch_log_group" "model_evaluator_logs" {
  name              = "/aws/lambda/mlops-model-evaluator-${var.bucket_name}"
  retention_in_days = 14
}
