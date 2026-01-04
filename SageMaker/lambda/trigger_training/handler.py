import os
import json
import boto3
import logging
import urllib3
from urllib.parse import quote

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# GitHub API configuration
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_OWNER = os.environ.get('GITHUB_OWNER')
GITHUB_REPO = os.environ.get('GITHUB_REPO')
WORKFLOW_ID = os.environ.get('WORKFLOW_ID', 'mlops.yml')

def lambda_handler(event, context):
    """
    Lambda function to trigger GitHub workflow when new training data is uploaded to S3.
    
    This function is triggered by EventBridge when new files are uploaded to s3://bucket/data/train/
    It calls the GitHub workflow_dispatch API to start the MLOps workflow.
    """
    logger.info('Received event: %s', json.dumps(event))
    
    try:
        # Extract S3 event details
        detail = event.get('detail', {})
        request_params = detail.get('requestParameters', {})
        bucket = request_params.get('bucketName')
        key = request_params.get('key')
        
        if not bucket or not key:
            logger.error('Could not extract bucket and key from event')
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing bucket or key in event'})
            }
        
        # Validate that this is a training data upload
        if not key.startswith('data/train/'):
            logger.info('Ignoring upload to %s - not in data/train/ path', key)
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Ignored - not training data'})
            }
        
        logger.info('Training data uploaded: s3://%s/%s', bucket, key)
        
        # Trigger GitHub workflow
        success = trigger_github_workflow(bucket, key)
        
        if success:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'GitHub workflow triggered successfully',
                    'trigger_reason': f'New training data uploaded: {key}'
                })
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to trigger GitHub workflow'})
            }
            
    except Exception as e:
        logger.exception('Unhandled exception in lambda')
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }

def trigger_github_workflow(bucket, key):
    """
    Trigger GitHub workflow using the workflow_dispatch API.
    
    Args:
        bucket: S3 bucket name where data was uploaded
        key: S3 object key that was uploaded
        
    Returns:
        bool: True if workflow was triggered successfully, False otherwise
    """
    if not GITHUB_TOKEN or not GITHUB_OWNER or not GITHUB_REPO:
        logger.error('Missing required GitHub configuration: GITHUB_TOKEN, GITHUB_OWNER, or GITHUB_REPO')
        return False
    
    # GitHub API URL for workflow dispatch
    url = f'https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_ID}/dispatches'
    
    # Prepare the request payload
    payload = {
        'ref': 'main',  # or 'master' depending on your default branch
        'inputs': {
            'trigger_reason': f'Event-driven: New training data uploaded to s3://{bucket}/{key}',
            'data_path': f's3://{bucket}/{key}',
            'triggered_by': 'lambda'
        }
    }
    
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json',
        'User-Agent': 'AWS-Lambda-MLOps-Trigger'
    }
    
    try:
        # Use urllib3 for HTTP requests (available in Lambda runtime)
        http = urllib3.PoolManager()
        
        logger.info('Triggering GitHub workflow at %s', url)
        logger.info('Payload: %s', json.dumps(payload))
        
        response = http.request(
            'POST',
            url,
            body=json.dumps(payload).encode('utf-8'),
            headers=headers
        )
        
        logger.info('GitHub API response status: %d', response.status)
        logger.info('GitHub API response body: %s', response.data.decode('utf-8'))
        
        if response.status == 204:
            logger.info('GitHub workflow triggered successfully')
            return True
        else:
            logger.error('GitHub API returned status %d: %s', response.status, response.data.decode('utf-8'))
            return False
            
    except Exception as e:
        logger.exception('Error calling GitHub API: %s', str(e))
        return False