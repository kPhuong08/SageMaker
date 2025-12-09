import os
import json
import boto3
import logging
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sagemaker = boto3.client('sagemaker')

BUCKET = os.environ.get('BUCKET_NAME')
SAGEMAKER_ROLE = os.environ.get('SAGEMAKER_ROLE_ARN')
ENDPOINT_NAME = os.environ.get('ENDPOINT_NAME')
REGION = os.environ.get('REGION', 'us-east-1')

def _model_name_from_key(key):
    base = key.replace('/', '-').replace('.', '-')
    ts = int(time.time())
    return f"model-{base}-{ts}"

def _endpoint_config_name(model_name):
    return f"cfg-{model_name}"

def lambda_handler(event, context):
    logger.info('Received event: %s', json.dumps(event))

    # CloudTrail-based EventBridge events include S3 bucket/key in requestParameters
    try:
        detail = event.get('detail', {})
        request_params = detail.get('requestParameters', {})
        bucket = request_params.get('bucketName') or BUCKET
        key = None
        # try different shapes
        if 'key' in request_params:
            key = request_params['key']
        else:
            # For PutObject the CloudTrail event may include additional data in 'resources' or 'responseElements'
            key = detail.get('additionalEventData', {}).get('objectKey') or detail.get('requestParameters', {}).get('key')

        if not key:
            # Try eventRecords (S3 event style)
            records = event.get('Records', [])
            if records:
                s3 = records[0].get('s3', {})
                bucket = s3.get('bucket', {}).get('name', bucket)
                key = s3.get('object', {}).get('key')

        if not key:
            logger.error('Could not determine S3 object key from event')
            return {
                'statusCode': 400,
                'body': 'No S3 object key found in event'
            }

        s3_uri = f"s3://{bucket}/{key}"
        model_name = _model_name_from_key(key)
        cfg_name = _endpoint_config_name(model_name)

        # Create SageMaker model
        primary_container = {
            'Image': os.environ.get('INFERENCE_IMAGE', f'763104351884.dkr.ecr.{REGION}.amazonaws.com/huggingface-pytorch-inference:latest'),
            'ModelDataUrl': s3_uri,
        }

        logger.info('Creating SageMaker model %s with model data %s', model_name, s3_uri)
        sagemaker.create_model(
            ModelName=model_name,
            PrimaryContainer=primary_container,
            ExecutionRoleArn=SAGEMAKER_ROLE
        )

        # Create endpoint config (simple single-variant)
        logger.info('Creating endpoint config %s', cfg_name)
        sagemaker.create_endpoint_config(
            EndpointConfigName=cfg_name,
            ProductionVariants=[
                {
                    'VariantName': 'AllTraffic',
                    'ModelName': model_name,
                    'InitialInstanceCount': int(os.environ.get('INSTANCE_COUNT', '1')),
                    'InstanceType': os.environ.get('INSTANCE_TYPE', 'ml.m5.large'),
                    'InitialVariantWeight': 1.0
                }
            ]
        )

        # If endpoint exists -> update it, otherwise create it
        try:
            logger.info('Checking if endpoint %s exists', ENDPOINT_NAME)
            sagemaker.describe_endpoint(EndpointName=ENDPOINT_NAME)
            # Update endpoint to use new config
            logger.info('Updating endpoint %s to use config %s', ENDPOINT_NAME, cfg_name)
            sagemaker.update_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=cfg_name)
        except sagemaker.exceptions.ClientError as e:
            if 'Could not find' in str(e) or 'ResourceNotFound' in str(e):
                logger.info('Endpoint %s not found, creating new endpoint', ENDPOINT_NAME)
                sagemaker.create_endpoint(EndpointName=ENDPOINT_NAME, EndpointConfigName=cfg_name)
            else:
                logger.exception('Error describing or creating/updating endpoint')
                raise

        return {
            'statusCode': 200,
            'body': json.dumps({'model': model_name, 'endpoint_config': cfg_name, 's3_uri': s3_uri})
        }

    except Exception:
        logger.exception('Unhandled exception in lambda')
        raise
