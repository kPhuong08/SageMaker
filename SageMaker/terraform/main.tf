provider "aws" {
  region = var.aws_region
}

module "s3" {
  source = "./modules/s3"

  bucket_name = var.bucket_name
  create_bucket = var.create_bucket
  existing_bucket_name = var.existing_bucket_name
}

module "iam" {
  source = "./modules/iam"

  s3_bucket = module.s3.s3_bucket_name
  bucket_arn  = "arn:aws:s3:::${module.s3.s3_bucket_name}"
  create_bucket = var.create_bucket
}

# Package Lambda Function
#data "archive_file" "lambda_zip_path" {
#  type        = "zip"
#  source_file = var.source_file
#  output_path = "${path.module}/../lambda/redeploy_endpoint/redeploy.zip"
#}

# Removed: GitHub workflow trigger Lambda is no longer needed for event-driven architecture

# Package Training Orchestrator Lambda Function
data "archive_file" "training_orchestrator_zip_path" {
  type        = "zip"
  source_file = var.training_orchestrator_source_file
  output_path = "${path.module}/../lambda/training_orchestrator/training_orchestrator.zip"
}

# Package Model Evaluator Lambda Function
data "archive_file" "model_evaluator_zip_path" {
  type        = "zip"
  source_file = var.model_evaluator_source_file
  output_path = "${path.module}/../lambda/model_evaluator/model_evaluator.zip"
}

# Package Deployment Orchestrator Lambda Function
data "archive_file" "deployment_orchestrator_zip_path" {
  type        = "zip"
  source_file = var.deployment_orchestrator_source_file
  output_path = "${path.module}/../lambda/deployment_orchestrator/deployment_orchestrator.zip"
}

#module "lambda" {
#  source = "./modules/lambda"

#  lambda_zip_path            = data.archive_file.lambda_zip_path.output_path
#  lambda_handler             = var.lambda_handler
#  bucket_name                = module.s3.s3_bucket_name
#  bucket_arn                 = "arn:aws:s3:::${module.s3.s3_bucket_name}"
#  lambda_role_arn            = module.iam.lambda_role_arn
#  sagemaker_role_arn         = module.iam.sagemaker_role_arn
#  endpoint_name              = var.endpoint_name
#  region                     = var.aws_region
#  trigger_type               = "eventbridge"  # Force event-driven architecture
#  serverless_memory_mb       = var.serverless_memory_mb
#  serverless_max_concurrency = var.serverless_max_concurrency
#  inference_image            = var.inference_image
#  # Legacy variables removed - no longer needed for serverless endpoints
#}

# Removed: GitHub workflow trigger module is no longer needed for event-driven architecture

module "lambda_training_orchestrator" {
  source = "./modules/lambda_training_orchestrator"

  lambda_zip_path    = data.archive_file.training_orchestrator_zip_path.output_path
  lambda_handler     = var.training_orchestrator_handler
  bucket_name        = module.s3.s3_bucket_name
  lambda_role_arn    = module.iam.lambda_role_arn
  sagemaker_role_arn = module.iam.sagemaker_role_arn
  region             = var.aws_region
  sns_topic_arn      = module.monitoring.sns_topic_arn
}

module "lambda_model_evaluator" {
  source = "./modules/lambda_model_evaluator"

  lambda_zip_path = data.archive_file.model_evaluator_zip_path.output_path
  lambda_handler  = var.model_evaluator_handler
  bucket_name     = module.s3.s3_bucket_name
  lambda_role_arn = module.iam.lambda_role_arn
  region          = var.aws_region
  sns_topic_arn   = module.monitoring.sns_topic_arn
}

module "lambda_deployment_orchestrator" {
  source = "./modules/lambda_deployment_orchestrator"

  lambda_zip_path             = data.archive_file.deployment_orchestrator_zip_path.output_path
  lambda_handler              = var.deployment_orchestrator_handler
  bucket_name                 = module.s3.s3_bucket_name
  lambda_role_arn             = module.iam.lambda_role_arn
  sagemaker_role_arn          = module.iam.sagemaker_role_arn
  endpoint_name               = var.endpoint_name
  region                      = var.aws_region
  serverless_memory_mb        = var.serverless_memory_mb
  serverless_max_concurrency  = var.serverless_max_concurrency
  inference_image             = var.inference_image
  sns_topic_arn               = module.monitoring.sns_topic_arn
}

module "eventbridge" {
  source = "./modules/eventbridge"

  bucket_name                          = module.s3.s3_bucket_name
  create_bucket                        = var.create_bucket
  existing_bucket_name                 = var.existing_bucket_name
  training_orchestrator_lambda_arn     = module.lambda_training_orchestrator.lambda_function_arn
  training_orchestrator_lambda_name    = module.lambda_training_orchestrator.lambda_function_name
  model_evaluator_lambda_arn           = module.lambda_model_evaluator.lambda_function_arn
  model_evaluator_lambda_name          = module.lambda_model_evaluator.lambda_function_name
  deployment_orchestrator_lambda_arn   = module.lambda_deployment_orchestrator.lambda_function_arn
  deployment_orchestrator_lambda_name  = module.lambda_deployment_orchestrator.lambda_function_name
  
  depends_on = [
    module.lambda_training_orchestrator,
    module.lambda_model_evaluator,
    module.lambda_deployment_orchestrator
  ]
}

module "monitoring" {
  source = "./modules/monitoring"

  endpoint_name                    = var.endpoint_name
  region                          = var.aws_region
  environment                     = var.environment
  alert_email                     = var.alert_email
  error_rate_threshold            = var.error_rate_threshold
  latency_threshold_ms            = var.latency_threshold_ms
  training_lambda_function_name   = module.lambda_training_orchestrator.lambda_function_name
  model_evaluator_lambda_function_name = module.lambda_model_evaluator.lambda_function_name
  deployment_lambda_function_name = module.lambda_deployment_orchestrator.lambda_function_name
}


