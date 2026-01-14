# Terraform Variables Configuration
# Copy this file and customize the values for your environment

# AWS Configuration
aws_region = "us-east-1"

# S3 Bucket Configuration
bucket_name = "atml-models-bucket"  # Change this to a unique bucket name
create_bucket = true

# SageMaker Endpoint Configuration
endpoint_name = "serverless-inference-endpoint"

# Serverless Endpoint Configuration
serverless_memory_mb = 4096        # Memory in MB (1024, 2048, 3072, 4096, 5120, 6144)
serverless_max_concurrency = 10    # Max concurrent requests (1-200)

# Monitoring and Alerting Configuration
environment = "production"
alert_email = "tk.phuong08@gmail.com"                   # Set to your email address to receive alarm notifications
                                  # Example: "admin@company.com"

# Alarm Thresholds
error_rate_threshold = 5          # Number of 5XX errors before alarm triggers
latency_threshold_ms = 3000       # P99 latency threshold in milliseconds

# Note: Event-driven architecture is now the default
# GitHub workflow triggering has been removed in favor of pure AWS event-driven orchestration