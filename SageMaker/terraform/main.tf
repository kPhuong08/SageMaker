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

  bucket_name = module.s3.s3_bucket_name
  bucket_arn  = "arn:aws:s3:::${module.s3.s3_bucket_name}"
  create_bucket = var.create_bucket
}

# Package Lambda Function
data "archive_file" "lambda_zip_path" {
  type        = "zip"
  source_file = var.source_file
  output_path = "${path.module}/../lambda/redeploy_endpoint/redeploy.zip"
}

# Package Trigger Training Lambda Function
data "archive_file" "trigger_lambda_zip_path" {
  count       = var.enable_training_trigger ? 1 : 0
  type        = "zip"
  source_file = var.trigger_source_file
  output_path = "${path.module}/../lambda/trigger_training/trigger_training.zip"
}

module "lambda" {
  source = "./modules/lambda"

  lambda_zip_path            = data.archive_file.lambda_zip_path.output_path
  lambda_handler             = var.lambda_handler
  bucket_name                = module.s3.s3_bucket_name
  bucket_arn                 = "arn:aws:s3:::${module.s3.s3_bucket_name}"
  lambda_role_arn            = module.iam.lambda_role_arn
  sagemaker_role_arn         = module.iam.sagemaker_role_arn
  endpoint_name              = var.endpoint_name
  region                     = var.aws_region
  trigger_type               = var.trigger_type
  serverless_memory_mb       = var.serverless_memory_mb
  serverless_max_concurrency = var.serverless_max_concurrency
  inference_image            = var.inference_image
  # Legacy variables (deprecated)
  instance_type              = var.instance_type
  instance_count             = var.instance_count
}

module "lambda_trigger" {
  count  = var.enable_training_trigger ? 1 : 0
  source = "./modules/lambda_trigger"

  lambda_zip_path  = data.archive_file.trigger_lambda_zip_path[0].output_path
  lambda_handler   = var.trigger_lambda_handler
  bucket_name      = module.s3.s3_bucket_name
  lambda_role_arn  = module.iam.lambda_role_arn
  github_token     = var.github_token
  github_owner     = var.github_owner
  github_repo      = var.github_repo
  workflow_id      = var.workflow_id
}

module "eventbridge" {
  source = "./modules/eventbridge"

  bucket_name                     = module.s3.s3_bucket_name
  create_bucket                   = var.create_bucket
  existing_bucket_name            = var.existing_bucket_name
  trigger_type                    = var.trigger_type
  lambda_function_arn             = module.lambda.lambda_function_arn
  lambda_function_name            = module.lambda.lambda_function_name
  enable_training_trigger         = var.enable_training_trigger
  training_lambda_function_arn    = var.enable_training_trigger ? module.lambda_trigger[0].lambda_function_arn : ""
  training_lambda_function_name   = var.enable_training_trigger ? module.lambda_trigger[0].lambda_function_name : ""
  depends_on = [module.lambda]
}

module "monitoring" {
  source = "./modules/monitoring"

  endpoint_name        = var.endpoint_name
  region               = var.aws_region
  environment          = var.environment
  alert_email          = var.alert_email
  error_rate_threshold = var.error_rate_threshold
  latency_threshold_ms = var.latency_threshold_ms
  lambda_function_name = module.lambda.lambda_function_name
}


