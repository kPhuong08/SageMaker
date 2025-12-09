output "event_rule_arn" {
  value = aws_cloudwatch_event_rule.s3_put_rule.arn
}

output "trigger_type" {
  value = var.trigger_type
}