output "lambda_function_name" {
  value = aws_lambda_function.training_orchestrator.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.training_orchestrator.arn
}