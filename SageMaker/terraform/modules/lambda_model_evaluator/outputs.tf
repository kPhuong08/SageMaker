output "lambda_function_name" {
  description = "Name of the Model Evaluator Lambda function"
  value       = aws_lambda_function.model_evaluator.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Model Evaluator Lambda function"
  value       = aws_lambda_function.model_evaluator.arn
}

output "lambda_function_invoke_arn" {
  description = "Invoke ARN of the Model Evaluator Lambda function"
  value       = aws_lambda_function.model_evaluator.invoke_arn
}
