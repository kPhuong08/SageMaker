"""
Training Orchestrator Lambda Function

This Lambda function orchestrates the complete training pipeline:
1. Processes S3 events from data/train/* uploads
2. Starts SageMaker training jobs
3. Monitors training completion
4. Downloads and evaluates model artifacts
5. Uploads approved models to models/approved/

Triggered by: EventBridge S3 events from s3://bucket/data/train/*
"""

import json
import os
import boto3
import time
import logging
from datetime import datetime
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sagemaker_client = boto3.client('sagemaker')
s3_client = boto3.client('s3')
sns_client = boto3.client('sns')

# Environment variables
SAGEMAKER_ROLE = os.environ.get('SAGEMAKER_ROLE_ARN')
TRAINING_IMAGE = os.environ.get('TRAINING_IMAGE', '763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-training:1.13.1-transformers4.26.0-gpu-py39-cu117-ubuntu20.04')
INSTANCE_TYPE = os.environ.get('TRAINING_INSTANCE_TYPE', 'ml.m5.xlarge')
INSTANCE_COUNT = int(os.environ.get('TRAINING_INSTANCE_COUNT', '1'))
MAX_RUNTIME_SECONDS = int(os.environ.get('MAX_RUNTIME_SECONDS', '3600'))  # 1 hour
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
S3_BUCKET = os.environ.get('BUCKET_NAME')


def lambda_handler(event, context):
    """
    Main Lambda handler for training orchestration.
    
    This function only starts the training job and returns immediately.
    Model evaluation will be handled by a separate Lambda function triggered
    by EventBridge when the training job completes.
    
    Args:
        event: EventBridge S3 event
        context: Lambda context
        
    Returns:
        dict: Response with training job name and status
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract S3 information from EventBridge event
        s3_info = extract_s3_info_from_event(event)
        logger.info(f"Processing S3 event: {s3_info}")
        
        # Start SageMaker training job
        training_job_name = start_training_job(s3_info)
        logger.info(f"Started training job: {training_job_name}")
        
        # Send notification that training started
        send_training_started_notification(training_job_name, s3_info)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Training job started successfully',
                'training_job_name': training_job_name,
                'data_source': s3_info['s3_uri']
            })
        }
            
    except Exception as e:
        logger.error(f"Lambda execution failed: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f"Lambda execution failed: {str(e)}"
            })
        }

def extract_s3_info_from_event(event):
    """
    Extract S3 bucket and key information from EventBridge S3 event.
    
    Args:
        event: EventBridge event containing S3 information
        
    Returns:
        dict: S3 information with bucket and key
    """
    try:
        # EventBridge S3 event structure
        detail = event['detail']
        bucket = detail['bucket']['name']
        key = detail['object']['key']
        
        return {
            'bucket': bucket,
            'key': key,
            's3_uri': f's3://{bucket}/{key}',
            'data_path': f's3://{bucket}/{os.path.dirname(key)}/'
        }
    except KeyError as e:
        raise ValueError(f"Invalid S3 event structure. Missing key: {e}")

def get_latest_training_code_uri(bucket):
    """Tìm file code (tar.gz) mới nhất trong folder models/code/"""
    try:
        prefix = 'models/code/'
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        
        if 'Contents' not in response:
            raise ValueError(f"No training code found in s3://{bucket}/{prefix}")
            
        # Oreder by time
        latest_file = sorted(response['Contents'], key=lambda x: x['LastModified'])[-1]
        key = latest_file['Key']
        
        return f"s3://{bucket}/{key}"
    except Exception as e:
        logger.error(f"Failed to find latest training code: {str(e)}")
        raise

def start_training_job(s3_info):
    """
    Start a SageMaker training job with the provided data.
    
    Args:
        s3_info: Dictionary containing S3 bucket and key information
        
    Returns:
        str: Training job name
    """
    # Get bucket name forn event
    bucket_name = s3_info['bucket']
    
    # Find newest code training
    code_s3_uri = get_latest_training_code_uri(bucket_name)
    logger.info(f"Using training code from: {code_s3_uri}")

    # Generate unique training job name
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    training_job_name = f"training-job-{timestamp}"
    
    # Prepare training job configuration
    training_config = {
        'TrainingJobName': training_job_name,
        'RoleArn': SAGEMAKER_ROLE,
        'AlgorithmSpecification': {
            'TrainingImage': TRAINING_IMAGE,
            'TrainingInputMode': 'File'
        },
        'HyperParameters': {
            'sagemaker_program': 'src/train.py',  # file in folder src
            'sagemaker_submit_directory': code_s3_uri, # File tar.gz have code
            'epochs': '5',
            'batch_size': '32',
            'learning_rate': '2e-5',
            'sagemaker_container_log_level': '20',
            'sagemaker_region': os.environ.get('AWS_REGION', 'us-east-1')
        },
        'InputDataConfig': [
            {
                'ChannelName': 'train',
                'DataSource': {
                    'S3DataSource': {
                        'S3DataType': 'S3Prefix',
                        'S3Uri': s3_info['data_path'],
                        'S3DataDistributionType': 'FullyReplicated'
                    }
                },
                'ContentType': 'text/csv',
                'CompressionType': 'None'
            }
        ],
        'OutputDataConfig': {
            'S3OutputPath': f's3://{os.environ.get("S3_BUCKET", S3_BUCKET)}/models/raw/'
        },
        'ResourceConfig': {
            'InstanceType': INSTANCE_TYPE,
            'InstanceCount': INSTANCE_COUNT,
            'VolumeSizeInGB': 30
        },
        'StoppingCondition': {
            'MaxRuntimeInSeconds': MAX_RUNTIME_SECONDS
        },
        'Tags': [
            {
                'Key': 'Project',
                'Value': 'MLOps-Pipeline'
            },
            {
                'Key': 'TriggerSource',
                'Value': 'EventDriven'
            },
            {
                'Key': 'DataSource',
                'Value': s3_info['s3_uri']
            }
        ]
    }
    
    # Start training job
    response = sagemaker_client.create_training_job(**training_config)
    logger.info(f"Training job created: {response['TrainingJobArn']}")
    
    return training_job_name


def send_training_started_notification(training_job_name, s3_info):
    """
    Send SNS notification that training has started.
    
    Args:
        training_job_name: Name of the training job
        s3_info: S3 information about the training data
    """
    if not SNS_TOPIC_ARN:
        logger.info("SNS_TOPIC_ARN not configured - skipping notification")
        return
    
    try:
        message = f"""
MLOps Training Pipeline - TRAINING STARTED

Training Job: {training_job_name}
Status: Training job has been started

Data Source: {s3_info['s3_uri']}

The training job is now running. You will receive another notification when:
- Training completes successfully and model evaluation begins
- Training fails

You can monitor the training job in the SageMaker console or CloudWatch logs.
"""
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"MLOps Pipeline - Training Started",
            Message=message
        )
        
        logger.info("Training started notification sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send training started notification: {str(e)}")