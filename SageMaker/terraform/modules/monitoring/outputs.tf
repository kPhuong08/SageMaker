# Outputs for CloudWatch Monitoring Module

output "sns_topic_arn" {
  description = "ARN of the SNS topic for alerts"
  value       = aws_sns_topic.mlops_alerts.arn
}

output "dashboard_name" {
  description = "Name of the CloudWatch dashboard"
  value       = aws_cloudwatch_dashboard.mlops_dashboard.dashboard_name
}

output "dashboard_url" {
  description = "URL to view the CloudWatch dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home?region=${var.region}#dashboards:name=${aws_cloudwatch_dashboard.mlops_dashboard.dashboard_name}"
}

output "alarm_arns" {
  description = "ARNs of all CloudWatch alarms"
  value = {
    high_error_rate       = aws_cloudwatch_metric_alarm.high_error_rate.arn
    high_latency          = aws_cloudwatch_metric_alarm.high_latency.arn
    training_job_failure  = aws_cloudwatch_metric_alarm.training_job_failure.arn
  }
}
