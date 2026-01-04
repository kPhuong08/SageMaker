# CloudWatch Monitoring Module for MLOps Pipeline
# Creates dashboards and alarms for SageMaker training jobs and endpoints

locals {
  alarm_namespace = "AWS/SageMaker"
}

# SNS Topic for Alarm Notifications
resource "aws_sns_topic" "mlops_alerts" {
  name = "mlops-alerts-${var.endpoint_name}"
  
  tags = {
    Name        = "MLOps Alerts"
    Environment = var.environment
  }
}

# SNS Topic Subscription (Email)
resource "aws_sns_topic_subscription" "email_subscription" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.mlops_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "mlops_dashboard" {
  dashboard_name = "MLOps-${var.endpoint_name}"

  dashboard_body = jsonencode({
    widgets = [
      # Endpoint Invocations
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SageMaker", "Invocations", { stat = "Sum", label = "Total Invocations" }],
            [".", "Invocation4XXErrors", { stat = "Sum", label = "4XX Errors" }],
            [".", "Invocation5XXErrors", { stat = "Sum", label = "5XX Errors" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.region
          title  = "Endpoint Invocations"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      # Endpoint Latency
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SageMaker", "ModelLatency", { stat = "Average", label = "Avg Latency" }],
            ["...", { stat = "p99", label = "P99 Latency" }],
            [".", "OverheadLatency", { stat = "Average", label = "Overhead (Cold Start)" }]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "Endpoint Latency (ms)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      # Model Setup Time (Serverless Cold Start)
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SageMaker", "ModelSetupTime", { stat = "Average", label = "Avg Setup Time" }],
            ["...", { stat = "Maximum", label = "Max Setup Time" }]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "Model Setup Time - Cold Start (ms)"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      # Memory Utilization
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/SageMaker", "MemoryUtilization", { stat = "Average", label = "Memory Usage %" }]
          ]
          period = 300
          stat   = "Average"
          region = var.region
          title  = "Memory Utilization"
          yAxis = {
            left = {
              min = 0
              max = 100
            }
          }
        }
      },
      # Training Job Status (if available)
      {
        type = "log"
        properties = {
          query   = "SOURCE '/aws/sagemaker/TrainingJobs' | fields @timestamp, @message | filter @message like /Completed/ or @message like /Failed/ | sort @timestamp desc | limit 20"
          region  = var.region
          title   = "Recent Training Jobs"
        }
      }
    ]
  })
}

# Alarm: High Error Rate (5XX)
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "mlops-high-error-rate-${var.endpoint_name}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Invocation5XXErrors"
  namespace           = local.alarm_namespace
  period              = 300
  statistic           = "Sum"
  threshold           = var.error_rate_threshold
  alarm_description   = "Endpoint has high 5XX error rate"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = var.endpoint_name
    VariantName  = "AllTraffic"
  }

  alarm_actions = [aws_sns_topic.mlops_alerts.arn]
  ok_actions    = [aws_sns_topic.mlops_alerts.arn]

  tags = {
    Name        = "High Error Rate Alarm"
    Environment = var.environment
  }
}

# Alarm: High Latency (P99)
resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "mlops-high-latency-${var.endpoint_name}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ModelLatency"
  namespace           = local.alarm_namespace
  period              = 300
  statistic           = "Maximum"
  threshold           = var.latency_threshold_ms
  alarm_description   = "Endpoint P99 latency is too high"
  treat_missing_data  = "notBreaching"

  dimensions = {
    EndpointName = var.endpoint_name
    VariantName  = "AllTraffic"
  }

  alarm_actions = [aws_sns_topic.mlops_alerts.arn]
  ok_actions    = [aws_sns_topic.mlops_alerts.arn]

  tags = {
    Name        = "High Latency Alarm"
    Environment = var.environment
  }
}

# Alarm: Training Job Failures
# Note: This uses a metric filter on CloudWatch Logs
resource "aws_cloudwatch_log_metric_filter" "training_failures" {
  name           = "mlops-training-failures"
  log_group_name = "/aws/sagemaker/TrainingJobs"
  pattern        = "[time, request_id, event_type = TrainingJobStatus, status = Failed*]"

  metric_transformation {
    name      = "TrainingJobFailures"
    namespace = "MLOps"
    value     = "1"
  }
}

resource "aws_cloudwatch_metric_alarm" "training_job_failure" {
  alarm_name          = "mlops-training-job-failure"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "TrainingJobFailures"
  namespace           = "MLOps"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "SageMaker training job failed"
  treat_missing_data  = "notBreaching"

  alarm_actions = [aws_sns_topic.mlops_alerts.arn]

  tags = {
    Name        = "Training Job Failure Alarm"
    Environment = var.environment
  }
}

# Alarm: Lambda Function Errors (for redeploy_endpoint)
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  count               = var.lambda_function_name != "" ? 1 : 0
  alarm_name          = "mlops-lambda-errors-${var.lambda_function_name}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  alarm_description   = "Lambda function encountered errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = var.lambda_function_name
  }

  alarm_actions = [aws_sns_topic.mlops_alerts.arn]

  tags = {
    Name        = "Lambda Errors Alarm"
    Environment = var.environment
  }
}
