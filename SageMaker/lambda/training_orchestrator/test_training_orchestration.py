"""
Property-Based Tests for Training Orchestrator Lambda

Tests the training orchestration functionality using property-based testing
to verify correctness across a wide range of inputs.
"""

import json
import pytest
import string
from datetime import datetime
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import tarfile

# Import the handler module
import handler


class TestTrainingOrchestration:
    """
    Property-based tests for training orchestration functionality.
    """

    @given(
        bucket_name=st.text(
            min_size=3, 
            max_size=63, 
            alphabet=st.sampled_from(string.ascii_lowercase + string.digits + '-')
        ),
        object_key=st.text(
            min_size=1, 
            max_size=100, 
            alphabet=st.sampled_from(string.ascii_letters + string.digits + '/-._')
        ),
    )
    @settings(max_examples=100)
    def test_property_25_sagemaker_training_job_creation(self, bucket_name, object_key):
        """
        **Feature: mlops-refactor-enhancement, Property 25: SageMaker Training Job Creation**
        **Validates: Requirements 9.1, 9.2**
        
        Property: For any valid S3 event containing data paths, the training orchestrator
        should create a SageMaker training job with the correct S3 data paths as input channels.
        """
        # Ensure valid S3 bucket name format
        bucket_name = bucket_name.lower().replace('_', '-')
        if not bucket_name or bucket_name.startswith('-') or bucket_name.endswith('-'):
            bucket_name = f"test-bucket-{abs(hash(bucket_name)) % 1000}"
        
        # Ensure object key is in data/train/ path
        if not object_key.startswith('data/train/'):
            object_key = f"data/train/{object_key.lstrip('/')}"
        
        # Create valid EventBridge S3 event
        event = {
            'detail': {
                'bucket': {'name': bucket_name},
                'object': {'key': object_key}
            }
        }
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'SAGEMAKER_EXECUTION_ROLE_ARN': 'arn:aws:iam::123456789012:role/SageMakerRole',
            'S3_BUCKET': bucket_name,
            'TRAINING_INSTANCE_TYPE': 'ml.m5.xlarge',
            'TRAINING_INSTANCE_COUNT': '1',
            'MAX_RUNTIME_SECONDS': '3600'
        }):
            # Mock SageMaker client
            with patch('handler.sagemaker_client') as mock_sagemaker, \
                 patch('handler.s3_client') as mock_s3:
                
                # Setup Mock: S3 list_objects_v2 must return a fake file so get_latest_training_code_uri works
                mock_s3.list_objects_v2.return_value = {
                    'Contents': [
                        {
                            'Key': 'models/code/training_code_20230101.tar.gz',
                            'LastModified': datetime(2023, 1, 1)
                        }
                    ]
                }

                # Setup Mock: SageMaker create_training_job return value
                mock_sagemaker.create_training_job.return_value = {
                    'TrainingJobArn': f'arn:aws:sagemaker:us-east-1:123456789012:training-job/test-job'
                }

                # Extract S3 info from event
                s3_info = handler.extract_s3_info_from_event(event)
                
                # Start training job
                training_job_name = handler.start_training_job(s3_info)
                
                # Verify training job was created
                assert mock_sagemaker.create_training_job.called
                call_args = mock_sagemaker.create_training_job.call_args[1]
                
                # Property: Training job should be created with correct S3 data paths
                assert 'TrainingJobName' in call_args
                assert call_args['TrainingJobName'] == training_job_name
                
                # Property: Input data config should contain the correct S3 path
                input_data_config = call_args['InputDataConfig']
                assert len(input_data_config) == 1
                assert input_data_config[0]['ChannelName'] == 'training'
                
                # Property: S3 data source should point to the directory containing the uploaded data
                s3_data_source = input_data_config[0]['DataSource']['S3DataSource']
                expected_s3_path = f"s3://{bucket_name}/{os.path.dirname(object_key)}/"
                assert s3_data_source['S3Uri'] == expected_s3_path
                
                # Property: Output should be configured to models/raw/
                output_config = call_args['OutputDataConfig']
                assert output_config['S3OutputPath'] == f"s3://{bucket_name}/models/raw/"
                
                # Property: Resource configuration should match environment variables
                resource_config = call_args['ResourceConfig']
                assert resource_config['InstanceType'] == 'ml.m5.xlarge'
                assert resource_config['InstanceCount'] == 1

    @given(
        bucket_name=st.text(min_size=3, max_size=63, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')),
        training_job_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'Nd'), whitelist_characters='-')),
    )
    @settings(max_examples=50)
    def test_s3_info_extraction_from_event(self, bucket_name, training_job_name):
        """
        Property: For any valid EventBridge S3 event, the system should correctly
        extract bucket name and object key information.
        """
        # Ensure valid S3 bucket name format
        bucket_name = bucket_name.lower().replace('_', '-')
        if not bucket_name or bucket_name.startswith('-') or bucket_name.endswith('-'):
            bucket_name = f"test-bucket-{abs(hash(bucket_name)) % 1000}"
        
        object_key = f"data/train/{training_job_name}/data.csv"
        
        # Create EventBridge S3 event
        event = {
            'detail': {
                'bucket': {'name': bucket_name},
                'object': {'key': object_key}
            }
        }
        
        # Extract S3 info
        s3_info = handler.extract_s3_info_from_event(event)
        
        # Property: Extracted info should match event data
        assert s3_info['bucket'] == bucket_name
        assert s3_info['key'] == object_key
        assert s3_info['s3_uri'] == f"s3://{bucket_name}/{object_key}"
        assert s3_info['data_path'] == f"s3://{bucket_name}/{os.path.dirname(object_key)}/"

    def test_invalid_event_structure_handling(self):
        """
        Property: For any malformed EventBridge event, the system should raise
        a clear ValueError indicating the missing information.
        """
        # Test missing detail
        with pytest.raises(ValueError, match="Invalid S3 event structure"):
            handler.extract_s3_info_from_event({})
        
        # Test missing bucket
        with pytest.raises(ValueError, match="Invalid S3 event structure"):
            handler.extract_s3_info_from_event({
                'detail': {
                    'object': {'key': 'test.csv'}
                }
            })
        
        # Test missing object
        with pytest.raises(ValueError, match="Invalid S3 event structure"):
            handler.extract_s3_info_from_event({
                'detail': {
                    'bucket': {'name': 'test-bucket'}
                }
            })

    @given(
        accuracy=st.floats(min_value=0.0, max_value=1.0),
        f1_score=st.floats(min_value=0.0, max_value=1.0),
        precision=st.floats(min_value=0.0, max_value=1.0),
        recall=st.floats(min_value=0.0, max_value=1.0),
        threshold_accuracy=st.floats(min_value=0.0, max_value=1.0),
        threshold_f1=st.floats(min_value=0.0, max_value=1.0),
        threshold_precision=st.floats(min_value=0.0, max_value=1.0),
        threshold_recall=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_evaluation_threshold_comparison(self, accuracy, f1_score, precision, recall,
                                           threshold_accuracy, threshold_f1, threshold_precision, threshold_recall):
        """
        Property: For any set of metrics and thresholds, the evaluation should correctly
        determine pass/fail status based on whether ALL metrics meet their thresholds.
        """
        metrics = {
            'accuracy': accuracy,
            'f1_score': f1_score,
            'precision': precision,
            'recall': recall
        }
        
        thresholds = {
            'accuracy': threshold_accuracy,
            'f1_score': threshold_f1,
            'precision': threshold_precision,
            'recall': threshold_recall
        }
        
        # Perform evaluation
        result = handler.perform_evaluation(metrics, thresholds)
        
        # Property: Model should pass only if ALL metrics meet their thresholds
        expected_pass = all(
            metrics[metric] >= thresholds[metric]
            for metric in thresholds.keys()
        )
        
        assert result['passed'] == expected_pass
        
        # Property: Each metric result should correctly reflect pass/fail status
        for metric_name, threshold_value in thresholds.items():
            metric_result = result['results'][metric_name]
            expected_metric_pass = metrics[metric_name] >= threshold_value
            
            assert metric_result['passed'] == expected_metric_pass
            assert metric_result['value'] == metrics[metric_name]
            assert metric_result['threshold'] == threshold_value
            assert metric_result['status'] == ('pass' if expected_metric_pass else 'fail')
        
        # Property: Summary should correctly count passed/failed checks
        total_checks = len(thresholds)
        expected_passed_checks = sum(1 for metric in thresholds.keys() if metrics[metric] >= thresholds[metric])
        expected_failed_checks = total_checks - expected_passed_checks
        
        assert result['summary']['total_checks'] == total_checks
        assert result['summary']['passed_checks'] == expected_passed_checks
        assert result['summary']['failed_checks'] == expected_failed_checks
        assert result['summary']['pass_rate'] == (expected_passed_checks / total_checks if total_checks > 0 else 0)

    def test_metrics_extraction_from_valid_archive(self):
        """
        Property: For any valid model archive containing metrics.json,
        the system should successfully extract the metrics.
        """
        # Create a temporary model archive with metrics.json
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create metrics.json
            metrics_data = {
                'accuracy': 0.92,
                'f1_score': 0.88,
                'precision': 0.85,
                'recall': 0.91
            }
            
            metrics_path = os.path.join(tmpdir, 'metrics.json')
            with open(metrics_path, 'w') as f:
                json.dump(metrics_data, f)
            
            # Create model.tar.gz
            model_tar_path = os.path.join(tmpdir, 'model.tar.gz')
            with tarfile.open(model_tar_path, 'w:gz') as tar:
                tar.add(metrics_path, arcname='metrics.json')
            
            # Extract metrics
            extracted_metrics = handler.extract_metrics_from_model_archive(model_tar_path)
            
            # Property: Extracted metrics should match original data
            assert extracted_metrics == metrics_data

    def test_metrics_extraction_from_invalid_archive(self):
        """
        Property: For any model archive missing metrics.json,
        the system should raise a FileNotFoundError with clear message.
        """
        # Create a temporary model archive without metrics.json
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some other file
            dummy_path = os.path.join(tmpdir, 'model.pkl')
            with open(dummy_path, 'w') as f:
                f.write('dummy model data')
            
            # Create model.tar.gz without metrics.json
            model_tar_path = os.path.join(tmpdir, 'model.tar.gz')
            with tarfile.open(model_tar_path, 'w:gz') as tar:
                tar.add(dummy_path, arcname='model.pkl')
            
            # Property: Should raise FileNotFoundError for missing metrics.json
            with pytest.raises(FileNotFoundError, match="metrics.json not found in model archive"):
                handler.extract_metrics_from_model_archive(model_tar_path)

    @given(
        model_s3_path=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'Nd'), whitelist_characters='/-._')),
        training_job_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'Nd'), whitelist_characters='-')),
        accuracy=st.floats(min_value=0.0, max_value=1.0),
        f1_score=st.floats(min_value=0.0, max_value=1.0),
        precision=st.floats(min_value=0.0, max_value=1.0),
        recall=st.floats(min_value=0.0, max_value=1.0),
        threshold_accuracy=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=50)
    def test_property_26_model_evaluation_and_approval(self, model_s3_path, training_job_name, 
                                                      accuracy, f1_score, precision, recall, threshold_accuracy):
        """
        **Feature: mlops-refactor-enhancement, Property 26: Model Evaluation and Approval**
        **Validates: Requirements 9.3, 9.4, 9.5, 9.6**
        
        Property: For any model evaluation result, the approval workflow should correctly
        upload approved models to s3://bucket/models/approved/ only if evaluation passes,
        and log failures without uploading if evaluation fails.
        """
        # Ensure valid S3 path format
        if not model_s3_path.startswith('s3://'):
            model_s3_path = f"s3://test-bucket/models/raw/{model_s3_path.lstrip('/')}"
        
        # Create evaluation result based on whether metrics meet threshold
        evaluation_passed = accuracy >= threshold_accuracy
        
        evaluation_result = {
            'passed': evaluation_passed,
            'results': {
                'accuracy': {
                    'status': 'pass' if accuracy >= threshold_accuracy else 'fail',
                    'value': accuracy,
                    'threshold': threshold_accuracy,
                    'passed': accuracy >= threshold_accuracy
                },
                'f1_score': {
                    'status': 'pass',
                    'value': f1_score,
                    'threshold': 0.8,
                    'passed': True
                },
                'precision': {
                    'status': 'pass',
                    'value': precision,
                    'threshold': 0.75,
                    'passed': True
                },
                'recall': {
                    'status': 'pass',
                    'value': recall,
                    'threshold': 0.75,
                    'passed': True
                }
            },
            'summary': {
                'total_checks': 4,
                'passed_checks': 3 if evaluation_passed else 2,
                'failed_checks': 1 if not evaluation_passed else 2,
                'pass_rate': 0.75 if evaluation_passed else 0.5
            }
        }
        
        # Mock S3 client for upload operations
        with patch('handler.s3_client') as mock_s3:
            # Test model approval workflow
            approval_result = handler.handle_model_approval(
                model_s3_path, 
                evaluation_result, 
                training_job_name
            )
            
            # Property: Approval status should match evaluation result
            assert approval_result['approved'] == evaluation_passed
            
            if evaluation_passed:
                # Property: If evaluation passed, model should be uploaded to approved folder
                assert mock_s3.copy_object.called
                copy_call_args = mock_s3.copy_object.call_args[1]
                
                # Property: Approved model should be copied to models/approved/ path
                approved_key = copy_call_args['Key']
                assert approved_key.startswith('models/approved/')
                assert training_job_name in approved_key
                assert approved_key.endswith('/model.tar.gz')
                
                # Property: Approved path should be returned in result
                assert 'approved_path' in approval_result
                assert approval_result['approved_path'].startswith('s3://')
                assert 'models/approved' in approval_result['approved_path']
                
                # Property: Success message should be provided
                assert 'passed evaluation and was approved' in approval_result['message']
                
            else:
                # Property: If evaluation failed, no upload should occur
                assert not mock_s3.copy_object.called
                
                # Property: Failed metrics should be listed
                assert 'failed_metrics' in approval_result
                failed_metrics = approval_result['failed_metrics']
                assert 'accuracy' in failed_metrics  # accuracy should be the failing metric
                
                # Property: Failure message should be provided
                assert 'failed evaluation and was not approved' in approval_result['message']

    @given(
        bucket_name=st.text(min_size=3, max_size=63, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')),
        original_key=st.text(min_size=10, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'Nd'), whitelist_characters='/-._')),
        training_job_name=st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('L', 'Nd'), whitelist_characters='-')),
    )
    @settings(max_examples=50)
    def test_approved_model_upload_path_generation(self, bucket_name, original_key, training_job_name):
        """
        Property: For any approved model upload, the system should generate a unique
        path in the models/approved/ folder that includes the training job name.
        """
        # Ensure valid S3 bucket name format
        bucket_name = bucket_name.lower().replace('_', '-')
        if not bucket_name or bucket_name.startswith('-') or bucket_name.endswith('-'):
            bucket_name = f"test-bucket-{abs(hash(bucket_name)) % 1000}"
        
        # Ensure original key is in models/raw/ path
        if not original_key.startswith('models/raw/'):
            original_key = f"models/raw/{original_key.lstrip('/')}"
        
        model_s3_path = f"s3://{bucket_name}/{original_key}"
        
        # Mock S3 client
        with patch('handler.s3_client') as mock_s3:
            # Call upload_approved_model
            approved_path = handler.upload_approved_model(model_s3_path, training_job_name)
            
            # Property: S3 copy_object should be called
            assert mock_s3.copy_object.called
            copy_call_args = mock_s3.copy_object.call_args[1]
            
            # Property: Copy source should match original model path
            copy_source = copy_call_args['CopySource']
            assert copy_source['Bucket'] == bucket_name
            assert copy_source['Key'] == original_key
            
            # Property: Destination should be in models/approved/ folder
            approved_key = copy_call_args['Key']
            assert approved_key.startswith('models/approved/')
            assert training_job_name in approved_key
            assert approved_key.endswith('/model.tar.gz')
            
            # Property: Returned path should be valid S3 URI
            assert approved_path.startswith(f"s3://{bucket_name}/models/approved/")
            assert training_job_name in approved_path
            assert approved_path.endswith('/model.tar.gz')

    def test_model_approval_workflow_error_handling(self):
        """
        Property: For any S3 upload error during model approval, the system should
        return an approval failure with error details.
        """
        model_s3_path = "s3://test-bucket/models/raw/test-model.tar.gz"
        training_job_name = "test-training-job"
        
        # Create passing evaluation result
        evaluation_result = {
            'passed': True,
            'results': {
                'accuracy': {'passed': True, 'value': 0.9, 'threshold': 0.85}
            },
            'summary': {'passed_checks': 1, 'total_checks': 1}
        }
        
        # Mock S3 client to raise exception
        with patch('handler.s3_client') as mock_s3:
            mock_s3.copy_object.side_effect = Exception("S3 upload failed")
            
            # Test model approval workflow
            approval_result = handler.handle_model_approval(
                model_s3_path, 
                evaluation_result, 
                training_job_name
            )
            
            # Property: Approval should fail despite passing evaluation
            assert approval_result['approved'] == False
            
            # Property: Error should be captured in result
            assert 'error' in approval_result
            assert 'S3 upload failed' in approval_result['error']
            
            # Property: Appropriate message should be provided
            assert 'passed evaluation but approval upload failed' in approval_result['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])