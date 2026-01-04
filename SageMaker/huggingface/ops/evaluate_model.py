"""
Model Evaluation Script for MLOps Pipeline

This script downloads trained model artifacts from S3, parses metrics.json,
and evaluates against configurable quality thresholds.

Usage:
    python evaluate_model.py --model-uri s3://bucket/path/model.tar.gz --config config/thresholds.json
"""

import argparse
import os
import json
import tarfile
import tempfile
import sys
import boto3
from urllib.parse import urlparse


def download_from_s3(s3_uri, local_path):
    """
    Download file from S3.
    
    Args:
        s3_uri: S3 URI (s3://bucket/key)
        local_path: Local file path to save to
    """
    print(f"Downloading {s3_uri}...")
    
    # Parse S3 URI
    parsed = urlparse(s3_uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    
    # Download
    s3_client = boto3.client('s3')
    s3_client.download_file(bucket, key, local_path)
    
    print(f"✓ Downloaded to {local_path}")


def extract_metrics_from_model(model_tar_path):
    """
    Extract metrics.json from model.tar.gz archive.
    
    Args:
        model_tar_path: Path to model.tar.gz file
        
    Returns:
        dict: Metrics dictionary
    """
    print(f"Extracting metrics from {model_tar_path}...")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract tar.gz
        with tarfile.open(model_tar_path, 'r:gz') as tar:
            tar.extractall(tmpdir)
        
        # Find metrics.json
        metrics_path = os.path.join(tmpdir, 'metrics.json')
        
        if not os.path.exists(metrics_path):
            raise FileNotFoundError(
                f"metrics.json not found in model archive. "
                f"Training script must save metrics.json to SM_MODEL_DIR."
            )
        
        # Load metrics
        with open(metrics_path, 'r') as f:
            metrics = json.load(f)
        
        print(f"✓ Loaded metrics: {list(metrics.keys())}")
        return metrics


def load_thresholds(config_path):
    """
    Load evaluation thresholds from config file.
    
    Args:
        config_path: Path to thresholds JSON file
        
    Returns:
        dict: Thresholds dictionary
    """
    print(f"Loading thresholds from {config_path}...")
    
    with open(config_path, 'r') as f:
        thresholds = json.load(f)
    
    print(f"✓ Loaded thresholds: {thresholds}")
    return thresholds


def evaluate_metrics(metrics, thresholds):
    """
    Evaluate metrics against thresholds.
    
    Args:
        metrics: dict of metric values
        thresholds: dict of threshold values
        
    Returns:
        tuple: (passed: bool, report: dict)
    """
    print("\n" + "="*60)
    print("Evaluating Model")
    print("="*60)
    
    report = {
        'passed': True,
        'results': {},
        'summary': {}
    }
    
    # Check each threshold
    for metric_name, threshold_value in thresholds.items():
        if metric_name not in metrics:
            print(f"⚠ Warning: Metric '{metric_name}' not found in model metrics")
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
        
        status_symbol = "✓" if passed else "✗"
        print(f"{status_symbol} {metric_name}: {metric_value:.4f} (threshold: {threshold_value:.4f})")
        
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
    
    print("="*60)
    print(f"Summary: {passed_checks}/{total_checks} checks passed")
    print("="*60)
    
    return report['passed'], report


def main():
    parser = argparse.ArgumentParser(
        description='Evaluate trained model against quality thresholds'
    )
    parser.add_argument(
        '--model-uri',
        type=str,
        required=True,
        help='S3 URI of model artifact (model.tar.gz)'
    )
    parser.add_argument(
        '--config',
        type=str,
        required=True,
        help='Path to evaluation thresholds config file (JSON)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='evaluation_report.json',
        help='Path to save evaluation report (default: evaluation_report.json)'
    )
    
    args = parser.parse_args()
    
    try:
        # Download model from S3
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp_model:
            model_tar_path = tmp_model.name
        
        download_from_s3(args.model_uri, model_tar_path)
        
        # Extract metrics
        metrics = extract_metrics_from_model(model_tar_path)
        
        # Load thresholds
        thresholds = load_thresholds(args.config)
        
        # Evaluate
        passed, report = evaluate_metrics(metrics, thresholds)
        
        # Save report
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n✓ Evaluation report saved to {args.output}")
        
        # Print final result
        print("\n" + "="*60)
        if passed:
            print("✓ MODEL PASSED EVALUATION")
            print("Model meets all quality thresholds and is ready for deployment.")
        else:
            print("✗ MODEL FAILED EVALUATION")
            print("Model does not meet quality thresholds. Deployment will be skipped.")
        print("="*60)
        
        # Clean up
        os.remove(model_tar_path)
        
        # Exit with appropriate code
        sys.exit(0 if passed else 1)
        
    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Evaluation failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
