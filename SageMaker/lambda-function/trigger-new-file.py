import os
import json
import boto3
import time
from botocore.exceptions import ClientError 

sagemaker = boto3.client("sagemaker")

# --- CẤU HÌNH ---
CONTAINER_IMAGE = "763104351884.dkr.ecr.us-east-1.amazonaws.com/huggingface-pytorch-inference:1.13.1-transformers4.26.0-cpu-py39-ubuntu20.04"
ROLE_ARN = "arn:aws:iam::064197589739:role/service-role/SageMaker-MLOps"
ENDPOINT_NAME = "endpoint-serverless"

DEFAULT_MEMORY = 3072 
DEFAULT_CONCURRENCY = 5

# Định nghĩa tên gốc để dùng cho hàm dọn dẹp
BASE_NAME_CONFIG = "distilbert-config"
BASE_NAME_MODEL = "distilbert-model"

def cleanup_old_configs(keep_config_name):
    """Xóa Config cũ, giữ lại cái mới nhất"""
    print(f"--- Cleaning up configs (keeping {keep_config_name}) ---")
    try:
        paginator = sagemaker.get_paginator('list_endpoint_configs')
        page_iterator = paginator.paginate(NameContains=BASE_NAME_CONFIG)

        for page in page_iterator:
            for config in page['EndpointConfigs']:
                cfg_name = config['EndpointConfigName']
                if cfg_name == keep_config_name: continue
                
                try:
                    sagemaker.delete_endpoint_config(EndpointConfigName=cfg_name)
                    print(f"[Deleted Config] {cfg_name}")
                except ClientError as e:
                    # Bỏ qua nếu đang InUse
                    if "currently in use" in str(e) or "Referenced by" in str(e):
                        print(f"[Skipped Config] {cfg_name} is in use.")
                    else:
                        print(f"[Error Config] {cfg_name}: {e}")
    except Exception as e:
        print(f"Cleanup config error: {e}")

def cleanup_old_models(keep_model_name):
    """Xóa Model cũ, giữ lại cái mới nhất"""
    print(f"--- Cleaning up models (keeping {keep_model_name}) ---")
    try:
        paginator = sagemaker.get_paginator('list_models')
        page_iterator = paginator.paginate(NameContains=BASE_NAME_MODEL)

        for page in page_iterator:
            for model in page['Models']:
                mdl_name = model['ModelName']
                if mdl_name == keep_model_name: continue
                
                try:
                    sagemaker.delete_model(ModelName=mdl_name)
                    print(f"[Deleted Model] {mdl_name}")
                except ClientError as e:
                    if "currently in use" in str(e) or "referenced by" in str(e): 
                        print(f"[Skipped Model] {mdl_name} is in use.")
                    else:
                        print(f"[Error Model] {mdl_name}: {e}")
    except Exception as e:
        print(f"Cleanup model error: {e}")

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))
    
    # 1. Parse Event
    try:
        if 'detail' in event and 'bucket' in event['detail']:
            bucket = event['detail']['bucket']['name']
            key = event['detail']['object']['key']
        else:
            # Fallback cho test
            bucket = "sagemaker-automlops"
            key = "model/model.tar.gz"
    except Exception as e:
        return {'statusCode': 400, 'body': 'Invalid Event Format'}
        
    s3_model_uri = f"s3://{bucket}/{key}"
    timestamp = int(time.time())
    
    # Tạo tên với timestamp
    model_name = f"{BASE_NAME_MODEL}-{timestamp}"
    endpoint_config_name = f"{BASE_NAME_CONFIG}-{timestamp}"

    # 2. Create Model
    container_def = {
        "Image": CONTAINER_IMAGE,
        "ModelDataUrl": s3_model_uri,
        "Environment": {}
    }
    print(f"Creating model: {model_name}")
    sagemaker.create_model(
        ModelName=model_name,
        ExecutionRoleArn=ROLE_ARN,
        PrimaryContainer=container_def
    )

    # 3. Create Endpoint Config
    production_variants = [{
        "VariantName": "prod-variant",
        "ModelName": model_name,
        "ServerlessConfig": {
            "MemorySizeInMB": DEFAULT_MEMORY,
            "MaxConcurrency": DEFAULT_CONCURRENCY
        }
    }]
    print(f"Creating endpoint config: {endpoint_config_name}")
    sagemaker.create_endpoint_config(
        EndpointConfigName=endpoint_config_name,
        ProductionVariants=production_variants
    )

    # 4. Logic thông minh: Kiểm tra rồi mới Create hoặc Update
    try:
        # Kiểm tra xem endpoint có tồn tại không
        desc = sagemaker.describe_endpoint(EndpointName=ENDPOINT_NAME)
        status = desc['EndpointStatus']
        print(f"Endpoint '{ENDPOINT_NAME}' exists with status: {status}")
        
        # Nếu tồn tại -> Update
        if status in ['InService', 'Failed']:
            print(f"Updating endpoint to new config: {endpoint_config_name}")
            sagemaker.update_endpoint(
                EndpointName=ENDPOINT_NAME,
                EndpointConfigName=endpoint_config_name
            )
        elif status == 'Creating':
            print("Endpoint is already creating. Cannot update immediately.")
        elif status == 'Updating':
            print("Endpoint is already updating. Cannot update immediately.")
            
    except ClientError as e:
        # Nếu lỗi là "Could not find endpoint" -> Tạo mới
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationException' or error_code == 'ResourceNotFound':
            print(f"Endpoint '{ENDPOINT_NAME}' not found. Creating new one...")
            sagemaker.create_endpoint(
                EndpointName=ENDPOINT_NAME,
                EndpointConfigName=endpoint_config_name
            )
        else:
            # Nếu lỗi khác thì in ra log
            print(f"Unexpected error checking endpoint: {e}")
            raise e

    # 5. Dọn dẹp Config/Model cũ
    cleanup_old_configs(keep_config_name=endpoint_config_name)
    cleanup_old_models(keep_model_name=model_name)

    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Process started', 'config': endpoint_config_name})
    }