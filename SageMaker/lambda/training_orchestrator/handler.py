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
INSTANCE_TYPE = os.environ.get('TRAINING_INSTANCE_TYPE', 'ml.g4dn.xlarge')
INSTANCE_COUNT = int(os.environ.get('TRAINING_INSTANCE_COUNT', '1'))
MAX_RUNTIME_SECONDS = int(os.environ.get('MAX_RUNTIME_SECONDS', '3600'))  # 1 hour
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
S3_BUCKET = os.environ.get('S3_BUCKET')


def lambda_handler(event, context):
    """
    Main Lambda handler for training orchestration.
    
    Args:
        event: EventBridge S3 event
        context: Lambda context
        
    Returns:
        dict: Response with training status and results
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract S3 information from EventBridge event
        s3_info = extract_s3_info_from_event(event)
        logger.info(f"Processing S3 event: {s3_info}")
        
        # Start SageMaker training job
        training_job_name = start_training_job(s3_info)
        logger.info(f"Started training job: {training_job_name}")
        
        # Monitor training job completion
        training_result = monitor_training_job(training_job_name)
        logger.info(f"Training completed with status: {training_result['status']}")
        
        if training_result['status'] == 'Completed':
            # Evaluate model
            evaluation_result = evaluate_model(training_result['model_s3_path'])
            logger.info(f"Model evaluation result: {evaluation_result}")
            
            # Handle model approval workflow
            approval_result = handle_model_approval(
                training_result['model_s3_path'],
                evaluation_result,
                training_job_name
            )
            
            # Send notifications
            send_notification(training_job_name, evaluation_result, approval_result)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'training_job_name': training_job_name,
                    'training_status': training_result['status'],
                    'evaluation_passed': evaluation_result['passed'],
                    'model_approved': approval_result['approved'],
                    'approved_model_path': approval_result.get('approved_path')
                })
            }
        else:
            # Training failed
            error_msg = f"Training job {training_job_name} failed with status: {training_result['status']}"
            logger.error(error_msg)
            
            # Send failure notification
            send_failure_notification(training_job_name, training_result.get('failure_reason', 'Unknown'))
            
            return {
                'statusCode': 500,
                'body': json.dumps({
                    'error': error_msg,
                    'training_job_name': training_job_name,
                    'training_status': training_result['status'],
                    'failure_reason': training_result.get('failure_reason')
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


def start_training_job(s3_info):
    """
    Start a SageMaker training job with the provided data.
    
    Args:
        s3_info: Dictionary containing S3 bucket and key information
        
    Returns:
        str: Training job name
    """
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
        'InputDataConfig': [
            {
                'ChannelName': 'training',
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


def monitor_training_job(training_job_name):
    """
    Monitor SageMaker training job until completion.
    
    Args:
        training_job_name: Name of the training job to monitor
        
    Returns:
        dict: Training result with status and model S3 path
    """
    logger.info(f"Monitoring training job: {training_job_name}")
    
    while True:
        response = sagemaker_client.describe_training_job(TrainingJobName=training_job_name)
        status = response['TrainingJobStatus']
        
        logger.info(f"Training job status: {status}")
        
        if status in ['Completed', 'Failed', 'Stopped']:
            result = {
                'status': status,
                'training_job_name': training_job_name
            }
            
            if status == 'Completed':
                # Extract model artifact S3 path
                model_s3_path = response['ModelArtifacts']['S3ModelArtifacts']
                result['model_s3_path'] = model_s3_path
                logger.info(f"Model artifact saved to: {model_s3_path}")
            else:
                # Training failed or stopped
                result['failure_reason'] = response.get('FailureReason', 'Unknown failure')
                logger.error(f"Training failed: {result['failure_reason']}")
            
            return result
        
        # Wait before checking again
        time.sleep(30)


def evaluate_model(model_s3_path):
    """
    Evaluate model against quality thresholds.
    
    Args:
        model_s3_path: S3 path to model.tar.gz artifact
        
    Returns:
        dict: Evaluation result with passed status and detailed report
    """
    logger.info(f"Evaluating model: {model_s3_path}")
    
    try:
        # Download model artifact
        import tempfile
        import tarfile
        
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_model:
            model_tar_path = tmp_model.name
        
        # Parse S3 URI and download
        parsed = urlparse(model_s3_path)
        bucket = parsed.netloc
        key = parsed.path.lstrip('/')
        
        s3_client.download_file(bucket, key, model_tar_path)
        logger.info(f"Downloaded model to: {model_tar_path}")
        
        # Extract metrics.json from model archive
        metrics = extract_metrics_from_model_archive(model_tar_path)
        logger.info(f"Extracted metrics: {metrics}")
        
        # Load evaluation thresholds
        thresholds = load_evaluation_thresholds()
        logger.info(f"Using thresholds: {thresholds}")
        
        # Perform evaluation
        evaluation_result = perform_evaluation(metrics, thresholds)
        
        # Clean up temporary file
        os.remove(model_tar_path)
        
        return evaluation_result
        
    except Exception as e:
        logger.error(f"Model evaluation failed: {str(e)}", exc_info=True)
        return {
            'passed': False,
            'error': str(e),
            'results': {}
        }


def extract_metrics_from_model_archive(model_tar_path):
    """
    Extract metrics.json from model.tar.gz archive.
    
    Args:
        model_tar_path: Path to model.tar.gz file
        
    Returns:
        dict: Metrics dictionary
    """
    import tempfile
    import tarfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract tar.gz
        with tarfile.open(model_tar_path, 'r:gz') as tar:
            tar.extractall(tmpdir)
        
        # Find metrics.json
        metrics_path = os.path.join(tmpdir, 'metrics.json')
        
        if not os.path.exists(metrics_path):
            raise FileNotFoundError(
                "metrics.json not found in model archive. "
                "Training script must save metrics.json to SM_MODEL_DIR."
            )
        
        # Load metrics
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        
        return metrics


def load_evaluation_thresholds():
    """
    Load evaluation thresholds from S3 config file.
    
    Returns:
        dict: Thresholds dictionary
    """
    try:
        # Download thresholds config from S3
        config_key = 'config/evaluation_thresholds.json'
        
        response = s3_client.get_object(Bucket=S3_BUCKET, Key=config_key)
        thresholds = json.loads(response['Body'].read().decode('utf-8'))
        
        # Remove comment fields
        thresholds = {k: v for k, v in thresholds.items() if not k.startswith('_')}
        
        return thresholds
        
    except Exception as e:
        logger.warning(f"Could not load thresholds from S3: {e}. Using defaults.")
        # Default thresholds
        return {
            'accuracy': 0.85,
            'f1_score': 0.80,
            'precision': 0.75,
            'recall': 0.75
        }


def perform_evaluation(metrics, thresholds):
    """
    Evaluate metrics against thresholds.
    
    Args:
        metrics: dict of metric values
        thresholds: dict of threshold values
        
    Returns:
        dict: Evaluation result with passed status and detailed report
    """
    report = {
        'passed': True,
        'results': {},
        'summary': {}
    }
    
    # Check each threshold
    for metric_name, threshold_value in thresholds.items():
        if metric_name not in metrics:
            logger.warning(f"Metric '{metric_name}' not found in model metrics")
            report['results'][metric_name] = {
                'status': 'missing',
                'value': None,
                'threshold': threshold_value,
                'passed': False
            }
            report['passed'] = False
            continue
        
        metric_value = metrics[metric_name]
        passed = metric_value >= threshold_value
        
        logger.info(f"Metric {metric_name}: {metric_value:.4f} (threshold: {threshold_value:.4f}) - {'PASS' if passed else 'FAIL'}")
        
        report['results'][metric_name] = {
            'status': 'pass' if passed else 'fail',
            'value': metric_value,
            'threshold': threshold_value,
            'passed': passed
        }
        
        if not passed:
            report['passed'] = False
    
    # Add summary
    total_checks = len(thresholds)
    passed_checks = sum(1 for r in report['results'].values() if r['passed'])
    
    report['summary'] = {
        'total_checks': total_checks,
        'passed_checks': passed_checks,
        'failed_checks': total_checks - passed_checks,
        'pass_rate': passed_checks / total_checks if total_checks > 0 else 0
    }
    
    logger.info(f"Evaluation summary: {passed_checks}/{total_checks} checks passed")
    
    return report


def handle_model_approval(model_s3_path, evaluation_result, training_job_name):
    """
    Handle model approval workflow based on evaluation results.
    
    Args:
        model_s3_path: S3 path to model artifact
        evaluation_result: Result from model evaluation
        training_job_name: Name of the training job
        
    Returns:
        dict: Approval result with status and approved model path
    """
    if evaluation_result['passed']:
        # Model passed evaluation - upload to approved folder
        try:
            approved_path = upload_approved_model(model_s3_path, training_job_name)
            logger.info(f"Model approved and uploaded to: {approved_path}")
            
            return {
                'approved': True,
                'approved_path': approved_path,
                'message': 'Model passed evaluation and was approved for deployment'
            }
            
        except Exception as e:
            logger.error(f"Failed to upload approved model: {str(e)}")
            return {
                'approved': False,
                'error': f"Failed to upload approved model: {str(e)}",
                'message': 'Model passed evaluation but approval upload failed'
            }
    else:
        # Model failed evaluation - log failure
        logger.info("Model failed evaluation - not approved for deployment")
        
        return {
            'approved': False,
            'message': 'Model failed evaluation and was not approved for deployment',
            'failed_metrics': [
                metric for metric, result in evaluation_result['results'].items()
                if not result['passed']
            ]
        }


def upload_approved_model(model_s3_path, training_job_name):
    """
    Upload approved model to the approved models folder.
    
    Args:
        model_s3_path: Original S3 path to model artifact
        training_job_name: Name of the training job
        
    Returns:
        str: S3 path to approved model
    """
    # Parse original S3 path
    parsed = urlparse(model_s3_path)
    bucket = parsed.netloc
    original_key = parsed.path.lstrip('/')
    
    # Generate approved model key
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    approved_key = f"models/approved/{training_job_name}-{timestamp}/model.tar.gz"
    
    # Copy model to approved folder
    copy_source = {'Bucket': bucket, 'Key': original_key}
    s3_client.copy_object(
        CopySource=copy_source,
        Bucket=bucket,
        Key=approved_key,
        TaggingDirective='COPY'
    )
    
    approved_path = f"s3://{bucket}/{approved_key}"
    logger.info(f"Model copied to approved folder: {approved_path}")
    
    return approved_path


def send_notification(training_job_name, evaluation_result, approval_result):
    """
    Send SNS notification about training and evaluation results.
    
    Args:
        training_job_name: Name of the training job
        evaluation_result: Result from model evaluation
        approval_result: Result from model approval
    """
    if not SNS_TOPIC_ARN:
        logger.info("SNS_TOPIC_ARN not configured - skipping notification")
        return
    
    try:
        # Prepare notification message
        status = "SUCCESS" if approval_result['approved'] else "FAILED"
        
        message = f"""
MLOps Training Pipeline - {status}

Training Job: {training_job_name}
Status: Training completed successfully

Model Evaluation:
- Passed: {'Yes' if evaluation_result['passed'] else 'No'}
- Checks: {evaluation_result['summary']['passed_checks']}/{evaluation_result['summary']['total_checks']}

Model Approval:
- Approved: {'Yes' if approval_result['approved'] else 'No'}
- Message: {approval_result['message']}
"""
        
        if approval_result['approved']:
            message += f"\nApproved Model Path: {approval_result['approved_path']}"
        else:
            failed_metrics = approval_result.get('failed_metrics', [])
            if failed_metrics:
                message += f"\nFailed Metrics: {', '.join(failed_metrics)}"
        
        # Add detailed metrics
        message += "\n\nDetailed Results:"
        for metric, result in evaluation_result['results'].items():
            status_symbol = "✓" if result['passed'] else "✗"
            message += f"\n{status_symbol} {metric}: {result['value']:.4f} (threshold: {result['threshold']:.4f})"
        
        # Send notification
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"MLOps Pipeline - Training {status}",
            Message=message
        )
        
        logger.info("SNS notification sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send SNS notification: {str(e)}")


def send_failure_notification(training_job_name, failure_reason):
    """
    Send SNS notification about training failure.
    
    Args:
        training_job_name: Name of the failed training job
        failure_reason: Reason for training failure
    """
    if not SNS_TOPIC_ARN:
        logger.info("SNS_TOPIC_ARN not configured - skipping notification")
        return
    
    try:
        message = f"""
MLOps Training Pipeline - TRAINING FAILED

Training Job: {training_job_name}
Status: Training job failed

Failure Reason: {failure_reason}

Please check CloudWatch logs for detailed error information.
"""
        
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"MLOps Pipeline - Training FAILED",
            Message=message
        )
        
        logger.info("Failure notification sent successfully")
        
    except Exception as e:
        logger.error(f"Failed to send failure notification: {str(e)}")