output "training_event_rule_arn" {
  value       = aws_cloudwatch_event_rule.training_data_rule.arn
  description = "ARN of the training data EventBridge rule"
}

output "model_evaluation_event_rule_arn" {
  value       = aws_cloudwatch_event_rule.training_job_state_change_rule.arn
  description = "ARN of the training job state change EventBridge rule"
}

output "deployment_event_rule_arn" {
  value       = aws_cloudwatch_event_rule.approved_model_rule.arn
  description = "ARN of the approved model deployment EventBridge rule"
}