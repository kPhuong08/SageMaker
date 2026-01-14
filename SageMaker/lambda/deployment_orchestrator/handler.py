import os
import json
import boto3
import logging
import time
import tarfile
import tempfile
from urllib.parse import unquote_plus

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sagemaker = boto3.client('sagemaker')
s3 = boto3.client('s3')
sns = boto3.client('sns')

def _get_env_var(name, default=None):
    """Get environment variable with optional default"""
    return os.environ.get(name, default)

def _model_name_from_key(key):
    """Generate unique model name from S3 key"""
    base = key.replace('/', '-').replace('.', '-')
    ts = int(time.time())
    return f"model-{base}-{ts}"

def _endpoint_config_name(model_name):
    """Generate endpoint config name from model name"""
    return f"cfg-{model_name}"

def _validate_model_artifact(bucket, key):
    """
    Validate model artifact by checking if it's a valid tar.gz file
    and contains required files (model files)
    """
    try:
        logger.info(f"Validating model artifact s3://{bucket}/{key}")
        
        # Download the model artifact to a temporary file
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_file:
            s3.download_file(bucket, key, tmp_file.name)
            
            # Check if it's a valid tar.gz file
            with tarfile.open(tmp_file.name, 'r:gz') as tar:
                members = tar.getnames()
                logger.info(f"Model artifact contains files: {members}")
                
                # Basic validation - should contain some model files
                # This is a minimal check - in production you might want more specific validation
                if not members:
                    raise ValueError("Model artifact is empty")
                    
                # Check for common model file patterns
                has_model_files = any(
                    name.endswith(('.bin', '.pt', '.pth', '.pkl', '.json', '.txt'))
                    for name in members
                )
                
                if not has_model_files:
                    logger.warning("No recognized model files found, but proceeding with deployment")
                
        # Clean up temp file
        os.unlink(tmp_file.name)
        
        logger.info("Model artifact validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Model artifact validation failed: {str(e)}")
        return False

def _verify_endpoint_health(endpoint_name, max_wait_time=300):
    """
    Verify endpoint health by checking its status
    """
    try:
        logger.info(f"Verifying health of endpoint {endpoint_name}")
        
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            try:
                response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
                status = response['EndpointStatus']
                
                logger.info(f"Endpoint {endpoint_name} status: {status}")
                
                if status == 'InService':
                    logger.info(f"Endpoint {endpoint_name} is healthy and in service")
                    return True
                elif status in ['Failed', 'OutOfService']:
                    logger.error(f"Endpoint {endpoint_name} is in failed state: {status}")
                    return False
                else:
                    # Still creating/updating, wait a bit more
                    time.sleep(30)
                    
            except sagemaker.exceptions.ClientError as e:
                if 'Could not find' in str(e) or 'ResourceNotFound' in str(e):
                    logger.error(f"Endpoint {endpoint_name} not found")
                    return False
                else:
                    raise
        
        logger.error(f"Endpoint {endpoint_name} did not become healthy within {max_wait_time} seconds")
        return False
        
    except Exception as e:
        logger.error(f"Error verifying endpoint health: {str(e)}")
        return False

def _send_notification(subject, message):
    """Send SNS notification if topic is configured"""
    sns_topic_arn = _get_env_var('SNS_TOPIC_ARN')
    if sns_topic_arn:
        try:
            sns.publish(
                TopicArn=sns_topic_arn,
                Subject=subject,
                Message=message
            )
            logger.info(f"Sent notification: {subject}")
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")

def _rollback_deployment(endpoint_name, previous_config_name=None):
    """
    Attempt to rollback deployment by reverting to previous configuration
    This is a simplified rollback - in production you might want more sophisticated rollback logic
    """
    try:
        if previous_config_name:
            logger.info(f"Attempting rollback of endpoint {endpoint_name} to config {previous_config_name}")
            sagemaker.update_endpoint(
                EndpointName=endpoint_name,
                EndpointConfigName=previous_config_name
            )
            logger.info("Rollback initiated successfully")
        else:
            logger.warning("No previous configuration available for rollback")
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")

def lambda_handler(event, context):
    """
    Handle S3 events from models/approved/* to deploy approved models
    to SageMaker Serverless Endpoints
    """
    logger.info('Received event: %s', json.dumps(event))

    # Get environment variables
    BUCKET = _get_env_var('BUCKET_NAME')
    SAGEMAKER_ROLE = _get_env_var('SAGEMAKER_ROLE_ARN')
    ENDPOINT_NAME = _get_env_var('ENDPOINT_NAME')
    REGION = _get_env_var('REGION', 'us-east-1')
    SNS_TOPIC_ARN = _get_env_var('SNS_TOPIC_ARN')

    try:
        # Extract S3 event information
        # This Lambda should be triggered by S3 events from models/approved/*
        bucket = None
        key = None
        
        # Handle S3 event format (direct S3 events)
        if 'Records' in event:
            for record in event['Records']:
                if record.get('eventSource') == 'aws:s3':
                    bucket = record['s3']['bucket']['name']
                    key = unquote_plus(record['s3']['object']['key'])
                    break
        
        # Handle EventBridge format (S3 events via EventBridge)
        elif 'detail' in event:
            detail = event.get('detail', {})
            request_params = detail.get('requestParameters', {})
            bucket = request_params.get('bucketName') or BUCKET
            key = request_params.get('key')
            
            if not key:
                # Try different event formats
                key = detail.get('object', {}).get('key')
        
        if not bucket or not key:
            error_msg = 'Could not determine S3 bucket/key from event'
            logger.error(error_msg)
            return {
                'statusCode': 400,
                'body': json.dumps({'error': error_msg})
            }
        
        # Verify this is from the approved models path
        if not key.startswith('models/approved/'):
            logger.info(f"Ignoring event for non-approved model: {key}")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Event ignored - not from approved models path'})
            }
        
        logger.info(f"Processing approved model deployment: s3://{bucket}/{key}")
        
        # Step 1: Validate model artifact
        if not _validate_model_artifact(bucket, key):
            error_msg = f"Model artifact validation failed for s3://{bucket}/{key}"
            logger.error(error_msg)
            _send_notification(
                "Model Deployment Failed - Validation Error",
                f"Model artifact validation failed for {key}. Deployment aborted."
            )
            return {
                'statusCode': 400,
                'body': json.dumps({'error': error_msg})
            }
        
        # Step 2: Create SageMaker model
        s3_uri = f"s3://{bucket}/{key}"
        model_name = _model_name_from_key(key)
        cfg_name = _endpoint_config_name(model_name)
        
        primary_container = {
            'Image': _get_env_var('INFERENCE_IMAGE', f'763104351884.dkr.ecr.{REGION}.amazonaws.com/huggingface-pytorch-inference:latest'),
            'ModelDataUrl': s3_uri,
        }

        logger.info('Creating SageMaker model %s with model data %s', model_name, s3_uri)
        sagemaker.create_model(
            ModelName=model_name,
            PrimaryContainer=primary_container,
            ExecutionRoleArn=SAGEMAKER_ROLE
        )

        # Step 3: Create serverless endpoint config
        logger.info('Creating serverless endpoint config %s', cfg_name)
        
        # Get serverless configuration from environment variables
        memory_size_mb = int(_get_env_var('SERVERLESS_MEMORY_MB', '4096'))
        max_concurrency = int(_get_env_var('SERVERLESS_MAX_CONCURRENCY', '10'))
        
        logger.info('Serverless config: MemorySize=%dMB, MaxConcurrency=%d', memory_size_mb, max_concurrency)
        
        sagemaker.create_endpoint_config(
            EndpointConfigName=cfg_name,
            ProductionVariants=[
                {
                    'VariantName': 'AllTraffic',
                    'ModelName': model_name,
                    'ServerlessConfig': {
                        'MemorySizeInMB': memory_size_mb,
                        'MaxConcurrency': max_concurrency
                    }
                }
            ]
        )

        # Step 4: Get current endpoint config for potential rollback
        previous_config_name = None
        try:
            current_endpoint = sagemaker.describe_endpoint(EndpointName=ENDPOINT_NAME)
            previous_config_name = current_endpoint.get('EndpointConfigName')
            logger.info(f"Current endpoint config: {previous_config_name}")
        except Exception as e:
            if 'Could not find' in str(e) or 'ResourceNotFound' in str(e):
                logger.info('Endpoint does not exist yet, will create new one')
            else:
                logger.warning(f"Could not get current endpoint config: {str(e)}")

        # Step 5: Create or update endpoint
        try:
            if previous_config_name:
                logger.info('Updating endpoint %s to use config %s', ENDPOINT_NAME, cfg_name)
                sagemaker.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=cfg_name)
            else:
                logger.info('Creating new endpoint %s with config %s', ENDPOINT_NAME, cfg_name)
                sagemaker.create_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=cfg_name)
        except Exception as e:
            logger.error(f"Failed to create/update endpoint: {str(e)}")
            _send_notification(
                "Model Deployment Failed - Endpoint Error",
                f"Failed to create/update endpoint {ENDPOINT_NAME}: {str(e)}"
            )
            raise

        # Step 6: Verify endpoint health
        if not _verify_endpoint_health(ENDPOINT_NAME):
            error_msg = f"Endpoint {ENDPOINT_NAME} failed health check"
            logger.error(error_msg)
            
            # Attempt rollback
            _rollback_deployment(ENDPOINT_NAME, previous_config_name)
            
            _send_notification(
                "Model Deployment Failed - Health Check",
                f"Endpoint {ENDPOINT_NAME} failed health check. Rollback attempted."
            )
            
            return {
                'statusCode': 500,
                'body': json.dumps({'error': error_msg, 'rollback_attempted': True})
            }

        # Step 7: Success notification
        success_msg = f"Successfully deployed model {model_name} to endpoint {ENDPOINT_NAME}"
        logger.info(success_msg)
        
        _send_notification(
            "Model Deployment Successful",
            f"Model {model_name} successfully deployed to endpoint {ENDPOINT_NAME}\nModel URI: {s3_uri}"
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': success_msg,
                'model_name': model_name,
                'endpoint_config': cfg_name,
                'endpoint_name': ENDPOINT_NAME,
                's3_uri': s3_uri
            })
        }

    except Exception as e:
        error_msg = f"Unhandled exception in deployment orchestrator: {str(e)}"
        logger.exception(error_msg)
        
        _send_notification(
            "Model Deployment Failed - System Error",
            f"Deployment orchestrator encountered an error: {str(e)}"
        )
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }