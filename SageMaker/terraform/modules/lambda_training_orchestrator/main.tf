resource "aws_lambda_function" "training_orchestrator" {
  filename        = var.lambda_zip_path
  function_name   = "mlops-training-orchestrator-${var.bucket_name}"
  role     = var.lambda_role_arn
#  sagemaker_role  = var.sagemaker_role_arn
  handler         = var.lambda_handler
  runtime         = "python3.9"
  timeout         = 900  # 15 minutes for training orchestration
  memory_size     = 512

  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      BUCKET_NAME                = var.bucket_name
      SAGEMAKER_ROLE_ARN        = var.sagemaker_role_arn
      REGION                    = var.region
      EVALUATION_CONFIG_S3_PATH = "s3://${var.bucket_name}/config/evaluation_thresholds.json"
      SNS_TOPIC_ARN            = var.sns_topic_arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.training_orchestrator_logs,
  ]
}

resource "aws_cloudwatch_log_group" "training_orchestrator_logs" {
  name              = "/aws/lambda/mlops-training-orchestrator-${var.bucket_name}"
  retention_in_days = 14
}