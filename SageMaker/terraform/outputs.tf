output "s3_bucket" {
  value = module.s3.s3_bucket_name
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

output "training_event_rule_arn" {
  value       = module.eventbridge.training_event_rule_arn
  description = "ARN of the training data EventBridge rule"
}

