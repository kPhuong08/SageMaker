output "event_rule_arn" {
  value       = try(aws_cloudwatch_event_rule.s3_put_rule[0].arn, "")
  description = "ARN of the EventBridge rule (empty if trigger_type is 's3')"
}

output "training_event_rule_arn" {
  value       = try(aws_cloudwatch_event_rule.training_data_rule[0].arn, "")
  description = "ARN of the training data EventBridge rule (empty if enable_training_trigger is false)"
}

output "trigger_type" {
  value = var.trigger_type
}