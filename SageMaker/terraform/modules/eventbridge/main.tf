locals {
  bucket_name = var.create_bucket ? var.bucket_name : var.existing_bucket_name
  bucket_arn  = "arn:aws:s3:::${local.bucket_name}"
}

# EventBridge rule for training data uploads -> Training Orchestrator Lambda
resource "aws_cloudwatch_event_rule" "training_data_rule" {
  name = "mlops-training-data-uploaded-${replace(local.bucket_name, "[^a-zA-Z0-9_-]", "-")}"

  event_pattern = jsonencode({
    source = ["aws.s3"],
    detail-type = ["Object Created"],
    detail = {
      bucket = {
        name = [local.bucket_name]
      },
      object = {
        key = [{
          prefix = "data/train/"
        }]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "training_rule_target" {
  rule      = aws_cloudwatch_event_rule.training_data_rule.name
  target_id = "sendToTrainingOrchestratorLambda"
  arn       = var.training_orchestrator_lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge_training" {
  statement_id  = "AllowExecutionFromEventBridgeTraining"
  action        = "lambda:InvokeFunction"
  function_name = var.training_orchestrator_lambda_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.training_data_rule.arn
}

# EventBridge rule for SageMaker Training Job State Change -> Model Evaluator Lambda
resource "aws_cloudwatch_event_rule" "training_job_state_change_rule" {
  name        = "mlops-training-job-state-change-${replace(local.bucket_name, "[^a-zA-Z0-9_-]", "-")}"
  description = "Trigger Model Evaluator Lambda when SageMaker training job completes"

  event_pattern = jsonencode({
    source      = ["aws.sagemaker"],
    detail-type = ["SageMaker Training Job State Change"],
    detail = {
      TrainingJobStatus = ["Completed", "Failed", "Stopped"]
    }
  })
}

resource "aws_cloudwatch_event_target" "model_evaluator_rule_target" {
  rule      = aws_cloudwatch_event_rule.training_job_state_change_rule.name
  target_id = "sendToModelEvaluatorLambda"
  arn       = var.model_evaluator_lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge_model_evaluator" {
  statement_id  = "AllowExecutionFromEventBridgeModelEvaluator"
  action        = "lambda:InvokeFunction"
  function_name = var.model_evaluator_lambda_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.training_job_state_change_rule.arn
}

# EventBridge rule for approved model uploads -> Deployment Orchestrator Lambda
resource "aws_cloudwatch_event_rule" "approved_model_rule" {
  name = "mlops-approved-model-uploaded-${replace(local.bucket_name, "[^a-zA-Z0-9_-]", "-")}"

  event_pattern = jsonencode({
    source = ["aws.s3"],
    detail-type = ["Object Created"],
    detail = {
      bucket = {
        name = [local.bucket_name]
      },
      object = {
        key = [{
          prefix = "models/approved/"
        }]
      }
    }
  })
}

resource "aws_cloudwatch_event_target" "deployment_rule_target" {
  rule      = aws_cloudwatch_event_rule.approved_model_rule.name
  target_id = "sendToDeploymentOrchestratorLambda"
  arn       = var.deployment_orchestrator_lambda_arn
}

resource "aws_lambda_permission" "allow_eventbridge_deployment" {
  statement_id  = "AllowExecutionFromEventBridgeDeployment"
  action        = "lambda:InvokeFunction"
  function_name = var.deployment_orchestrator_lambda_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.approved_model_rule.arn
}
