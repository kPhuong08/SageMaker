locals {
  bucket_name = var.create_bucket ? var.bucket_name : var.existing_bucket_name
  bucket_arn  = "arn:aws:s3:::${local.bucket_name}"
}

# S3 notification -> Lambda (when using S3 notifications)
resource "aws_s3_bucket_notification" "notify_lambda" {
  count  = var.trigger_type == "s3" ? 1 : 0
  bucket = local.bucket_name

  lambda_function {
    lambda_function_arn = var.lambda_function_arn
    events              = ["s3:ObjectCreated:*"]
  }

  
}

# EventBridge rule (CloudTrail-based) -> Lambda
resource "aws_cloudwatch_event_rule" "s3_put_rule" {
  count = var.trigger_type == "eventbridge" ? 1 : 0

  name = "mlops-s3-object-created-${replace(local.bucket_name, "[^a-zA-Z0-9_-]", "-")}" 

  event_pattern = jsonencode({
    source = ["aws.s3"],
    detail-type = ["AWS API Call via CloudTrail"],
    detail = {
      eventName = ["PutObject", "CompleteMultipartUpload"],
      requestParameters = {
        bucketName = [local.bucket_name]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "rule_target" {
  count     = var.trigger_type == "eventbridge" ? 1 : 0
  rule      = aws_cloudwatch_event_rule.s3_put_rule[0].name
  target_id = "sendToLambda"
  arn       = var.lambda_function_arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  count         = var.trigger_type == "eventbridge" ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_put_rule[0].arn
}
