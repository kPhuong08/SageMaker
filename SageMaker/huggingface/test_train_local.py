"""
Local testing script for training code
Run this to verify training works before deploying to SageMaker
"""

import os
import sys
import shutil
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_training_local():
    """Test training script locally with sample data"""
    
    print("="*60)
    print("Testing Training Script Locally")
    print("="*60)
    
    # Create temporary directories
    with tempfile.TemporaryDirectory() as tmpdir:
        train_dir = os.path.join(tmpdir, 'train')
        model_dir = os.path.join(tmpdir, 'model')
        os.makedirs(train_dir)
        os.makedirs(model_dir)
        
        # Copy sample data
        sample_data = os.path.join(os.path.dirname(__file__), '..', 'examples', 'sample_data.csv')
        shutil.copy(sample_data, os.path.join(train_dir, 'data.csv'))
        
        print(f"\n✓ Created temp directories:")
        print(f"  Train: {train_dir}")
        print(f"  Model: {model_dir}")
        
        # Set environment variables
        os.environ['SM_MODEL_DIR'] = model_dir
        os.environ['SM_CHANNEL_TRAIN'] = train_dir
        
        # Prepare arguments
        sys.argv = [
            'train.py',
            '--epochs', '2',
            '--batch_size', '8',
            '--learning_rate', '2e-5',
            '--model_name', 'prajjwal1/bert-tiny',  # Use tiny model for fast testing
            '--max_length', '64',
            '--test_split', '0.2'
        ]
        
        print("\n✓ Configuration:")
        print(f"  Epochs: 2")
        print(f"  Batch size: 8")
        print(f"  Model: prajjwal1/bert-tiny (fast for testing)")
        print(f"  Test split: 0.2")
        
        # Import and run training
        print("\n" + "="*60)
        print("Starting Training...")
        print("="*60 + "\n")
        
        try:
            from train import train
            train()
            
            print("\n" + "="*60)
            print("✓ Training completed successfully!")
            print("="*60)
            
            # Check outputs
            print("\n✓ Checking outputs:")
            
            model_files = os.listdir(model_dir)
            print(f"  Model files: {model_files}")
            
            if 'metrics.json' in model_files:
                import json
                with open(os.path.join(model_dir, 'metrics.json'), 'r') as f:
                    metrics = json.load(f)
                
                print("\n✓ Metrics:")
                for key, value in metrics.items():
                    if isinstance(value, float):
                        print(f"  {key}: {value:.4f}")
                    else:
                        print(f"  {key}: {value}")
                
                # Check if metrics are valid
                print("\n✓ Validation:")
                if metrics['accuracy'] > 0:
                    print("  ✓ Accuracy > 0 - PASS")
                else:
                    print("  ✗ Accuracy = 0 - FAIL")
                
                if metrics['f1_score'] > 0:
                    print("  ✓ F1 Score > 0 - PASS")
                else:
                    print("  ✗ F1 Score = 0 - FAIL")
                
                return metrics
            else:
                print("  ✗ metrics.json not found!")
                return None
                
        except Exception as e:
            print(f"\n✗ Training failed: {e}")
            import traceback
            traceback.print_exc()
            return None

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Local Training Test")
    print("="*60)
    print("\nThis script tests the training code locally before deploying to SageMaker.")
    print("It uses a tiny model and small dataset for fast testing.\n")
    
    metrics = test_training_local()
    
    if metrics and metrics['accuracy'] > 0:
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED")
        print("="*60)
        print("\nYour training code is ready to deploy to SageMaker!")
        print("\nNext steps:")
        print("1. Package code: tar -czf sourcedir.tar.gz src/")
        print("2. Upload to S3: aws s3 cp sourcedir.tar.gz s3://YOUR_BUCKET/models/code/")
        print("3. Upload data: aws s3 cp data.csv s3://YOUR_BUCKET/data/train/")
    else:
        print("\n" + "="*60)
        print("✗ TESTS FAILED")
        print("="*60)
        print("\nPlease fix the issues above before deploying to SageMaker.")
