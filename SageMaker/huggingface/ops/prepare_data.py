"""
Data Preparation Script for MLOps Pipeline

This script prepares and uploads training data to S3 for SageMaker training jobs.
Supports CSV and JSON formats with automatic train/test splitting.

Usage:
    python prepare_data.py --data path/to/data.csv --bucket my-bucket
    python prepare_data.py --data path/to/data.json --bucket my-bucket --train-ratio 0.8
"""

import argparse
import os
import json
import pandas as pd
import boto3
from sklearn.model_selection import train_test_split
from datetime import datetime
import sys


def load_data(file_path):
    """
    Load data from CSV or JSON file.
    
    Args:
        file_path: Path to data file
        
    Returns:
        pandas DataFrame
    """
    print(f"Loading data from {file_path}...")
    
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.json'):
        df = pd.read_json(file_path)
    else:
        raise ValueError(f"Unsupported file format. Use .csv or .json")
    
    print(f"Loaded {len(df)} rows")
    return df


def validate_data(df):
    """
    Validate that data has required columns and no critical issues.
    
    Args:
        df: pandas DataFrame
        
    Returns:
        bool: True if valid
        
    Raises:
        ValueError: If validation fails
    """
    print("Validating data...")
    
    # Check required columns
    required_columns = ['text', 'label']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}. Data must have 'text' and 'label' columns.")
    
    # Check for null values in required columns
    null_counts = df[required_columns].isnull().sum()
    if null_counts.any():
        print(f"Warning: Found null values: {null_counts.to_dict()}")
        print("Removing rows with null values...")
        df = df.dropna(subset=required_columns)
        print(f"Remaining rows: {len(df)}")
    
    # Check if we have enough data
    if len(df) < 10:
        raise ValueError(f"Not enough data. Need at least 10 rows, got {len(df)}")
    
    # Check label types
    unique_labels = df['label'].unique()
    print(f"Found {len(unique_labels)} unique labels: {sorted(unique_labels)}")
    
    print("✓ Data validation passed")
    return df


def split_data(df, train_ratio=0.8, random_state=42):
    """
    Split data into train and test sets.
    
    Args:
        df: pandas DataFrame
        train_ratio: Ratio of training data (default: 0.8)
        random_state: Random seed for reproducibility
        
    Returns:
        tuple: (train_df, test_df)
    """
    print(f"Splitting data with train_ratio={train_ratio}...")
    
    train_df, test_df = train_test_split(
        df,
        train_size=train_ratio,
        random_state=random_state,
        stratify=df['label']  # Maintain label distribution
    )
    
    print(f"Train set: {len(train_df)} rows")
    print(f"Test set: {len(test_df)} rows")
    
    return train_df, test_df


def save_to_csv(df, file_path):
    """Save DataFrame to CSV file."""
    df.to_csv(file_path, index=False)
    print(f"Saved to {file_path}")


def upload_to_s3(local_file, bucket_name, s3_key):
    """
    Upload file to S3.
    
    Args:
        local_file: Path to local file
        bucket_name: S3 bucket name
        s3_key: S3 object key (path)
        
    Returns:
        str: S3 URI
    """
    s3_client = boto3.client('s3')
    
    print(f"Uploading {local_file} to s3://{bucket_name}/{s3_key}...")
    
    try:
        s3_client.upload_file(local_file, bucket_name, s3_key)
        s3_uri = f"s3://{bucket_name}/{s3_key}"
        print(f"✓ Uploaded to {s3_uri}")
        return s3_uri
    except Exception as e:
        print(f"✗ Upload failed: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Prepare and upload training data to S3 for SageMaker'
    )
    parser.add_argument(
        '--data',
        type=str,
        required=True,
        help='Path to input data file (CSV or JSON)'
    )
    parser.add_argument(
        '--bucket',
        type=str,
        required=True,
        help='S3 bucket name'
    )
    parser.add_argument(
        '--train-ratio',
        type=float,
        default=0.8,
        help='Ratio of training data (default: 0.8)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='./tmp',
        help='Local directory for temporary files (default: ./tmp)'
    )
    
    args = parser.parse_args()
    
    try:
        # Create output directory
        os.makedirs(args.output_dir, exist_ok=True)
        
        # Load and validate data
        df = load_data(args.data)
        df = validate_data(df)
        
        # Split data
        train_df, test_df = split_data(df, train_ratio=args.train_ratio)
        
        # Save to local CSV files
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        train_file = os.path.join(args.output_dir, f'train_{timestamp}.csv')
        test_file = os.path.join(args.output_dir, f'test_{timestamp}.csv')
        
        save_to_csv(train_df, train_file)
        save_to_csv(test_df, test_file)
        
        # Upload to S3
        print("\nUploading to S3...")
        train_s3_uri = upload_to_s3(
            train_file,
            args.bucket,
            f'data/train/train_{timestamp}.csv'
        )
        test_s3_uri = upload_to_s3(
            test_file,
            args.bucket,
            f'data/test/test_{timestamp}.csv'
        )
        
        # Print summary
        print("\n" + "="*60)
        print("✓ Data preparation complete!")
        print("="*60)
        print(f"Train data: {train_s3_uri}")
        print(f"Test data:  {test_s3_uri}")
        print(f"Total rows: {len(df)}")
        print(f"Train rows: {len(train_df)}")
        print(f"Test rows:  {len(test_df)}")
        print("="*60)
        
        # Clean up local files
        os.remove(train_file)
        os.remove(test_file)
        print(f"\nCleaned up temporary files")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
