output "s3_bucket" {
  value = module.s3.s3_bucket_name
}

output "lambda_function_arn" {
  value = module.lambda.lambda_function_arn
}

output "sagemaker_role_arn" {
  value = module.iam.sagemaker_role_arn
}

output "monitoring_dashboard_url" {
  value       = module.monitoring.dashboard_url
  description = "URL to CloudWatch dashboard"
}

output "monitoring_sns_topic_arn" {
  value       = module.monitoring.sns_topic_arn
  description = "SNS topic ARN for alerts"
}

output "lambda_zip_path" {
  value = var.lambda_zip_path
}
# Training Trigger Lambda Outputs
output "trigger_lambda_function_arn" {
  value       = var.enable_training_trigger ? module.lambda_trigger[0].lambda_function_arn : ""
  description = "ARN of the training trigger Lambda function"
}

output "trigger_lambda_function_name" {
  value       = var.enable_training_trigger ? module.lambda_trigger[0].lambda_function_name : ""
  description = "Name of the training trigger Lambda function"
}

output "training_event_rule_arn" {
  value       = module.eventbridge.training_event_rule_arn
  description = "ARN of the training data EventBridge rule"
}