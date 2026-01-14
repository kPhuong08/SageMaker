import os
import boto3
import sagemaker
from sagemaker.huggingface import HuggingFace

# Configuration: override with env vars or edit directly
ROLE = os.environ.get("SM_EXECUTION_ROLE", "arn:aws:iam::123456789012:role/sagemaker-execution-role")
BUCKET = os.environ.get("SM_BUCKET", "sagemaker-automlops")
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

def launch_training():
    print("Preparing HuggingFace estimator...")
    huggingface_estimator = HuggingFace(
        entry_point='train.py',
        source_dir='src',
        instance_type='ml.m5.xlarge',
        instance_count=1,
        role=ROLE,
        transformers_version='4.28.1',
        pytorch_version='2.0.0',
        py_version='py310',
        use_spot_instances=True,
        max_run=3600,
        max_wait=7200
    )

    print("Starting training job on SageMaker (this may take some time)...")
    huggingface_estimator.fit({
        'train': f's3://{BUCKET}/data/train',
        'test':  f's3://{BUCKET}/data/test'
    })

    model_data_s3 = huggingface_estimator.model_data
    print(f"Training complete. Model artifact: {model_data_s3}")

    with open("model_location.txt", "w") as f:
        f.write(model_data_s3)

    print("Wrote model_location.txt with S3 path.")


if __name__ == '__main__':
    launch_training()
