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

module "lambda" {
  source = "./modules/lambda"

  lambda_zip_path   = var.lambda_zip_path
  lambda_handler    = var.lambda_handler
  bucket_name       = module.s3.s3_bucket_name
  bucket_arn        = "arn:aws:s3:::${module.s3.s3_bucket_name}"
  lambda_role_arn   = module.iam.lambda_role_arn
  sagemaker_role_arn = module.iam.sagemaker_role_arn
  endpoint_name     = var.endpoint_name
  region            = var.aws_region
  trigger_type      = var.trigger_type
  instance_type     = var.instance_type
  instance_count    = var.instance_count
  inference_image   = var.inference_image
}

module "eventbridge" {
  source = "./modules/eventbridge"

  bucket_name = module.s3.s3_bucket_name
  create_bucket = var.create_bucket
  existing_bucket_name = var.existing_bucket_name
  trigger_type = var.trigger_type
  lambda_function_arn = module.lambda.lambda_function_arn
  lambda_function_name = module.lambda.lambda_function_name
  depends_on = [module.lambda]
}


output "s3_bucket" {
  value = module.s3.s3_bucket_name
}

output "lambda_function_arn" {
  value = module.lambda.lambda_function_arn
}

output "sagemaker_role_arn" {
  value = module.iam.sagemaker_role_arn
}