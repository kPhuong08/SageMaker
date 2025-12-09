resource "aws_lambda_function" "redeploy" {
  filename         = var.lambda_zip_path
  function_name    = "mlops-redeploy-${replace(var.bucket_name, "[^a-zA-Z0-9_-]", "-")}" 
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  handler          = var.lambda_handler
  runtime          = "python3.9"
  role             = var.lambda_role_arn

  environment {
    variables = {
      BUCKET_NAME           = var.bucket_name
      SAGEMAKER_ROLE_ARN    = var.sagemaker_role_arn
      ENDPOINT_NAME         = var.endpoint_name
      REGION                = var.region
      INSTANCE_TYPE         = var.instance_type
      INSTANCE_COUNT        = tostring(var.instance_count)
      INFERENCE_IMAGE       = var.inference_image
    }
  }
}

resource "aws_lambda_permission" "allow_s3" {
  count         = var.trigger_type == "s3" ? 1 : 0
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redeploy.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.bucket_arn
}
# Lambda function: expects a zip at `var.lambda_zip_path` relative to module
resource "aws_lambda_function" "redeploy" {
  filename         = var.lambda_zip_path
  function_name    = "mlops-redeploy-${replace(var.bucket_name, "[^a-zA-Z0-9_-]", "-")}" 
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  handler          = var.lambda_handler
  runtime          = "python3.9"
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      BUCKET_NAME           = local.bucket_name
      SAGEMAKER_ROLE_ARN    = aws_iam_role.sagemaker_execution_role.arn
      ENDPOINT_NAME         = var.endpoint_name
      REGION                = var.region
      INSTANCE_TYPE         = var.instance_type
      INSTANCE_COUNT        = tostring(var.instance_count)
      INFERENCE_IMAGE       = var.inference_image
    }
  }
}

resource "aws_lambda_permission" "allow_s3" {
  count         = var.trigger_type == "s3" ? 1 : 0
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redeploy.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = local.bucket_arn
}


resource "aws_lambda_permission" "allow_eventbridge" {
  count         = var.trigger_type == "eventbridge" ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redeploy.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_put_rule[0].arn
}
# Lambda function: expects a zip at `var.lambda_zip_path` relative to module
resource "aws_lambda_function" "redeploy" {
  filename         = var.lambda_zip_path
  function_name    = "mlops-redeploy-${replace(var.bucket_name, "[^a-zA-Z0-9_-]", "-")}" 
  source_code_hash = filebase64sha256(var.lambda_zip_path)
  handler          = var.lambda_handler
  runtime          = "python3.9"
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      BUCKET_NAME           = local.bucket_name
      SAGEMAKER_ROLE_ARN    = aws_iam_role.sagemaker_execution_role.arn
      ENDPOINT_NAME         = var.endpoint_name
      REGION                = var.region
      INSTANCE_TYPE         = var.instance_type
      INSTANCE_COUNT        = tostring(var.instance_count)
      INFERENCE_IMAGE       = var.inference_image
    }
  }
}

resource "aws_lambda_permission" "allow_s3" {
  count         = var.trigger_type == "s3" ? 1 : 0
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redeploy.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = local.bucket_arn
}


resource "aws_lambda_permission" "allow_eventbridge" {
  count         = var.trigger_type == "eventbridge" ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.redeploy.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_put_rule[0].arn
}