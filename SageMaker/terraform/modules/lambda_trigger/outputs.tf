output "lambda_function_name" {
  value = aws_lambda_function.trigger_training.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.trigger_training.arn
}