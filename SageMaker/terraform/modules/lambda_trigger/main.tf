# Lambda function for triggering GitHub workflows when training data is uploaded

resource "aws_lambda_function" "trigger_training" {
  filename         = var.lambda_zip_path
  function_name    = "mlops-trigger-training-${replace(var.bucket_name, "[^a-zA-Z0-9_-]", "-")}"
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  handler          = var.lambda_handler
  runtime          = "python3.9"
  role             = var.lambda_role_arn
  timeout          = 60

  environment {
    variables = {
      GITHUB_TOKEN  = var.github_token
      GITHUB_OWNER  = var.github_owner
      GITHUB_REPO   = var.github_repo
      WORKFLOW_ID   = var.workflow_id
    }
  }

  tags = {
    Name        = "MLOps Trigger Training"
    Environment = "production"
  }
}