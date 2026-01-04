"""
SageMaker Training Script with Real Fine-tuning

This script performs actual fine-tuning of pre-trained models using HuggingFace Trainer.
It loads data from SageMaker input channels, trains the model, and saves metrics.
"""

import argparse
import os
import json
import time
import pandas as pd
from datasets import Dataset
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    TrainingArguments,
    Trainer,
    DataCollatorWithPadding
)
from sklearn.metrics import accuracy_score, precision_recall_fscore_support


def load_data(data_path):
    """
    Load training data from SageMaker input channel.
    
    Args:
        data_path: Path to data directory (contains CSV files)
        
    Returns:
        pandas DataFrame
    """
    print(f"Loading data from {data_path}...")
    
    # Find CSV files in the directory
    csv_files = [f for f in os.listdir(data_path) if f.endswith('.csv')]
    
    if not csv_files:
        raise ValueError(f"No CSV files found in {data_path}")
    
    # Load the first CSV file (or combine multiple if needed)
    data_file = os.path.join(data_path, csv_files[0])
    df = pd.read_csv(data_file)
    
    print(f"Loaded {len(df)} examples from {csv_files[0]}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Validate required columns
    if 'text' not in df.columns or 'label' not in df.columns:
        raise ValueError("Data must have 'text' and 'label' columns")
    
    return df


def preprocess_data(df, tokenizer, max_length=128):
    """
    Preprocess data: tokenize text and create HuggingFace Dataset.
    
    Args:
        df: pandas DataFrame with 'text' and 'label' columns
        tokenizer: HuggingFace tokenizer
        max_length: Maximum sequence length
        
    Returns:
        HuggingFace Dataset
    """
    print(f"Preprocessing data with max_length={max_length}...")
    
    # Create HuggingFace Dataset
    dataset = Dataset.from_pandas(df[['text', 'label']])
    
    # Tokenization function
    def tokenize_function(examples):
        return tokenizer(
            examples['text'],
            padding='max_length',
            truncation=True,
            max_length=max_length
        )
    
    # Tokenize dataset
    tokenized_dataset = dataset.map(tokenize_function, batched=True)
    
    print(f"Preprocessed {len(tokenized_dataset)} examples")
    return tokenized_dataset


def compute_metrics(eval_pred):
    """
    Compute evaluation metrics.
    
    Args:
        eval_pred: Tuple of (predictions, labels)
        
    Returns:
        dict: Metrics dictionary
    """
    predictions, labels = eval_pred
    predictions = predictions.argmax(axis=-1)
    
    # Compute metrics
    accuracy = accuracy_score(labels, predictions)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average='weighted', zero_division=0
    )
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1
    }


def train():
    """Main training function."""
    # Parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--learning_rate", type=float, default=2e-5)
    parser.add_argument("--model_name", type=str, default="distilbert-base-uncased")
    parser.add_argument("--max_length", type=int, default=128)
    parser.add_argument("--model_dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--test", type=str, default=os.environ.get("SM_CHANNEL_TEST", "/opt/ml/input/data/test"))
    args = parser.parse_args()
    
    print("="*60)
    print("Starting SageMaker Training Job")
    print("="*60)
    print(f"Model: {args.model_name}")
    print(f"Epochs: {args.epochs}")
    print(f"Batch size: {args.batch_size}")
    print(f"Learning rate: {args.learning_rate}")
    print(f"Max length: {args.max_length}")
    print("="*60)
    
    start_time = time.time()
    
    try:
        # Load data
        train_df = load_data(args.train)
        test_df = load_data(args.test) if os.path.exists(args.test) else None
        
        # Get number of labels
        num_labels = train_df['label'].nunique()
        print(f"Number of labels: {num_labels}")
        
        # Load tokenizer and model
        print(f"\nLoading tokenizer and model: {args.model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(args.model_name)
        model = AutoModelForSequenceClassification.from_pretrained(
            args.model_name,
            num_labels=num_labels
        )
        
        # Preprocess data
        train_dataset = preprocess_data(train_df, tokenizer, args.max_length)
        test_dataset = preprocess_data(test_df, tokenizer, args.max_length) if test_df is not None else None
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir='/opt/ml/checkpoints',
            num_train_epochs=args.epochs,
            per_device_train_batch_size=args.batch_size,
            per_device_eval_batch_size=args.batch_size,
            learning_rate=args.learning_rate,
            weight_decay=0.01,
            logging_dir='/opt/ml/output/tensorboard',
            logging_steps=10,
            evaluation_strategy='epoch' if test_dataset else 'no',
            save_strategy='epoch',
            load_best_model_at_end=True if test_dataset else False,
            metric_for_best_model='accuracy' if test_dataset else None,
            save_total_limit=2,
            report_to='none'  # Disable wandb, etc.
        )
        
        # Data collator
        data_collator = DataCollatorWithPadding(tokenizer=tokenizer)
        
        # Initialize Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
            tokenizer=tokenizer,
            data_collator=data_collator,
            compute_metrics=compute_metrics if test_dataset else None
        )
        
        # Train
        print("\n" + "="*60)
        print("Starting training...")
        print("="*60)
        train_result = trainer.train()
        
        # Evaluate
        print("\n" + "="*60)
        print("Evaluating model...")
        print("="*60)
        
        if test_dataset:
            eval_results = trainer.evaluate()
            print(f"Evaluation results: {eval_results}")
        else:
            # If no test set, evaluate on train set
            eval_results = trainer.evaluate(train_dataset)
            print(f"Training set evaluation: {eval_results}")
        
        # Save model
        os.makedirs(args.model_dir, exist_ok=True)
        print(f"\nSaving model to {args.model_dir}...")
        trainer.save_model(args.model_dir)
        tokenizer.save_pretrained(args.model_dir)
        
        # Compute final metrics
        training_time = time.time() - start_time
        
        metrics = {
            'accuracy': eval_results.get('eval_accuracy', 0.0),
            'f1_score': eval_results.get('eval_f1_score', 0.0),
            'precision': eval_results.get('eval_precision', 0.0),
            'recall': eval_results.get('eval_recall', 0.0),
            'loss': eval_results.get('eval_loss', train_result.training_loss),
            'training_time_seconds': int(training_time),
            'num_examples': len(train_df),
            'num_epochs': args.epochs,
            'model_name': args.model_name
        }
        
        # Save metrics
        metrics_path = os.path.join(args.model_dir, "metrics.json")
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        
        print("\n" + "="*60)
        print("Training Complete!")
        print("="*60)
        print(f"Training time: {training_time:.2f} seconds")
        print(f"Final metrics:")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Training failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    train()
