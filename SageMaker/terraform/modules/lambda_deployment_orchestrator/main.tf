resource "aws_lambda_function" "deployment_orchestrator" {
  filename         = var.lambda_zip_path
  function_name    = "mlops-deployment-orchestrator-${var.bucket_name}"
  role            = var.lambda_role_arn
  handler         = var.lambda_handler
  runtime         = "python3.9"
  timeout         = 900  # 15 minutes for deployment orchestration
  memory_size     = 512

  source_code_hash = filebase64sha256(var.lambda_zip_path)

  environment {
    variables = {
      BUCKET_NAME                = var.bucket_name
      SAGEMAKER_ROLE_ARN        = var.sagemaker_role_arn
      ENDPOINT_NAME             = var.endpoint_name
      REGION                    = var.region
      SERVERLESS_MEMORY_MB      = var.serverless_memory_mb
      SERVERLESS_MAX_CONCURRENCY = var.serverless_max_concurrency
      INFERENCE_IMAGE           = var.inference_image
      SNS_TOPIC_ARN            = var.sns_topic_arn
    }
  }

  depends_on = [
    aws_cloudwatch_log_group.deployment_orchestrator_logs,
  ]
}

resource "aws_cloudwatch_log_group" "deployment_orchestrator_logs" {
  name              = "/aws/lambda/mlops-deployment-orchestrator-${var.bucket_name}"
  retention_in_days = 14
}