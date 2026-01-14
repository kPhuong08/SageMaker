"""
Property-Based Tests for Deployment Orchestrator Lambda

Tests the deployment orchestration functionality using property-based testing
to verify correctness across a wide range of inputs.
"""

import json
import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile
import tarfile

# Import the handler module
import handler


class TestDeploymentOrchestration:
    """
    Property-based tests for deployment orchestration functionality.
    """

    @given(
        bucket_name=st.text(min_size=3, max_size=63, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')),
        object_key=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'Nd'), whitelist_characters='/-._')),
    )
    @settings(max_examples=100)
    def test_property_28_approved_model_deployment(self, bucket_name, object_key):
        """
        **Feature: mlops-refactor-enhancement, Property 28: Approved Model Deployment**
        **Validates: Requirements 10.1, 10.2, 10.3**
        
        Property: For any model uploaded to s3://bucket/models/approved/, the deployment Lambda
        should create a new SageMaker model and serverless endpoint configuration.
        """
        # Ensure valid S3 bucket name format
        bucket_name = bucket_name.lower().replace('_', '-')
        if not bucket_name or bucket_name.startswith('-') or bucket_name.endswith('-'):
            bucket_name = f"test-bucket-{abs(hash(bucket_name)) % 1000}"
        
        # Ensure object key is in models/approved/ path
        if not object_key.startswith('models/approved/'):
            object_key = f"models/approved/{object_key.lstrip('/')}"
        
        # Create valid S3 event for approved model
        event = {
            'Records': [{
                'eventSource': 'aws:s3',
                's3': {
                    'bucket': {'name': bucket_name},
                    'object': {'key': object_key}
                }
            }]
        }
        
        # Mock environment variables
        with patch.dict(os.environ, {
            'BUCKET_NAME': bucket_name,
            'SAGEMAKER_ROLE_ARN': 'arn:aws:iam::123456789012:role/SageMakerRole',
            'ENDPOINT_NAME': 'test-endpoint',
            'REGION': 'us-east-1',
            'SERVERLESS_MEMORY_MB': '4096',
            'SERVERLESS_MAX_CONCURRENCY': '10'
        }, clear=True):
            # Mock AWS clients
            with patch('handler.sagemaker') as mock_sagemaker, \
                 patch('handler.s3') as mock_s3, \
                 patch('handler._validate_model_artifact') as mock_validate, \
                 patch('handler._verify_endpoint_health') as mock_health:
                
                # Setup mocks
                mock_validate.return_value = True
                mock_health.return_value = True
                
                # Mock SageMaker describe_endpoint to simulate existing endpoint
                mock_sagemaker.describe_endpoint.return_value = {
                    'EndpointConfigName': 'old-config'
                }
                
                # Call the handler
                context = Mock()
                result = handler.lambda_handler(event, context)
                
                # Verify the result indicates success
                assert result['statusCode'] == 200
                response_body = json.loads(result['body'])
                assert 'model_name' in response_body
                assert 'endpoint_config' in response_body
                assert 'endpoint_name' in response_body
                assert response_body['endpoint_name'] == 'test-endpoint'
                
                # Verify SageMaker model was created
                mock_sagemaker.create_model.assert_called_once()
                create_model_call = mock_sagemaker.create_model.call_args
                assert create_model_call[1]['ExecutionRoleArn'] == 'arn:aws:iam::123456789012:role/SageMakerRole'
                assert create_model_call[1]['PrimaryContainer']['ModelDataUrl'] == f"s3://{bucket_name}/{object_key}"
                
                # Verify endpoint config was created with serverless configuration
                mock_sagemaker.create_endpoint_config.assert_called_once()
                config_call = mock_sagemaker.create_endpoint_config.call_args
                production_variants = config_call[1]['ProductionVariants']
                assert len(production_variants) == 1
                assert 'ServerlessConfig' in production_variants[0]
                serverless_config = production_variants[0]['ServerlessConfig']
                assert serverless_config['MemorySizeInMB'] == 4096
                assert serverless_config['MaxConcurrency'] == 10
                
                # Verify endpoint was updated (since we mocked an existing endpoint)
                mock_sagemaker.update_endpoint.assert_called_once()
                update_call = mock_sagemaker.update_endpoint.call_args
                assert update_call[1]['EndpointName'] == 'test-endpoint'
                
                # Verify model artifact validation was called
                mock_validate.assert_called_once_with(bucket_name, object_key)
                
                # Verify endpoint health check was called
                mock_health.assert_called_once_with('test-endpoint')

    @given(
        bucket_name=st.text(min_size=3, max_size=63, alphabet=st.characters(whitelist_categories=('Ll', 'Nd'), whitelist_characters='-')),
        object_key=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('L', 'Nd'), whitelist_characters='/-._')),
        memory_mb=st.integers(min_value=1024, max_value=6144),
        max_concurrency=st.integers(min_value=1, max_value=200)
    )
    @settings(max_examples=100)
    def test_property_29_serverless_endpoint_configuration(self, bucket_name, object_key, memory_mb, max_concurrency):
        """
        **Feature: mlops-refactor-enhancement, Property 29: Serverless Endpoint Configuration**
        **Validates: Requirements 10.4**
        
        Property: For any endpoint deployment, the configuration should use SageMaker Serverless
        Endpoint settings (not real-time instances).
        """
        # Ensure valid S3 bucket name format
        bucket_name = bucket_name.lower().replace('_', '-')
        if not bucket_name or bucket_name.startswith('-') or bucket_name.endswith('-'):
            bucket_name = f"test-bucket-{abs(hash(bucket_name)) % 1000}"
        
        # Ensure object key is in models/approved/ path
        if not object_key.startswith('models/approved/'):
            object_key = f"models/approved/{object_key.lstrip('/')}"
        
        # Create valid S3 event for approved model
        event = {
            'Records': [{
                'eventSource': 'aws:s3',
                's3': {
                    'bucket': {'name': bucket_name},
                    'object': {'key': object_key}
                }
            }]
        }
        
        # Mock environment variables with custom serverless settings
        with patch.dict(os.environ, {
            'BUCKET_NAME': bucket_name,
            'SAGEMAKER_ROLE_ARN': 'arn:aws:iam::123456789012:role/SageMakerRole',
            'ENDPOINT_NAME': 'test-endpoint',
            'REGION': 'us-east-1',
            'SERVERLESS_MEMORY_MB': str(memory_mb),
            'SERVERLESS_MAX_CONCURRENCY': str(max_concurrency)
        }, clear=True):
            # Mock AWS clients
            with patch('handler.sagemaker') as mock_sagemaker, \
                 patch('handler.s3') as mock_s3, \
                 patch('handler._validate_model_artifact') as mock_validate, \
                 patch('handler._verify_endpoint_health') as mock_health:
                
                # Setup mocks
                mock_validate.return_value = True
                mock_health.return_value = True
                
                # Mock SageMaker describe_endpoint to simulate no existing endpoint
                mock_sagemaker.describe_endpoint.side_effect = Exception("ResourceNotFound")
                
                # Call the handler
                context = Mock()
                result = handler.lambda_handler(event, context)
                
                # Verify the result indicates success
                assert result['statusCode'] == 200
                
                # Verify endpoint config was created with correct serverless configuration
                mock_sagemaker.create_endpoint_config.assert_called_once()
                config_call = mock_sagemaker.create_endpoint_config.call_args
                production_variants = config_call[1]['ProductionVariants']
                assert len(production_variants) == 1
                
                # Verify ServerlessConfig is present (not InstanceType/InitialInstanceCount)
                variant = production_variants[0]
                assert 'ServerlessConfig' in variant
                assert 'InstanceType' not in variant
                assert 'InitialInstanceCount' not in variant
                
                # Verify serverless configuration values
                serverless_config = variant['ServerlessConfig']
                assert serverless_config['MemorySizeInMB'] == memory_mb
                assert serverless_config['MaxConcurrency'] == max_concurrency
                
                # Verify new endpoint was created (not updated)
                mock_sagemaker.create_endpoint.assert_called_once()
                create_call = mock_sagemaker.create_endpoint.call_args
                assert create_call[1]['EndpointName'] == 'test-endpoint'

    def test_non_approved_model_ignored(self):
        """
        Test that events for non-approved models are ignored
        """
        # Create event for non-approved model path
        event = {
            'Records': [{
                'eventSource': 'aws:s3',
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'models/raw/some-model.tar.gz'}
                }
            }]
        }
        
        with patch.dict(os.environ, {
            'BUCKET_NAME': 'test-bucket',
            'ENDPOINT_NAME': 'test-endpoint'
        }, clear=True):
            context = Mock()
            result = handler.lambda_handler(event, context)
            
            # Should return success but ignore the event
            assert result['statusCode'] == 200
            response_body = json.loads(result['body'])
            assert 'ignored' in response_body['message'].lower()

    def test_model_validation_failure(self):
        """
        Test that deployment fails when model validation fails
        """
        event = {
            'Records': [{
                'eventSource': 'aws:s3',
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'models/approved/invalid-model.tar.gz'}
                }
            }]
        }
        
        with patch.dict(os.environ, {
            'BUCKET_NAME': 'test-bucket',
            'ENDPOINT_NAME': 'test-endpoint'
        }, clear=True):
            with patch('handler._validate_model_artifact') as mock_validate:
                mock_validate.return_value = False
                
                context = Mock()
                result = handler.lambda_handler(event, context)
                
                # Should return error status
                assert result['statusCode'] == 400
                response_body = json.loads(result['body'])
                assert 'validation failed' in response_body['error'].lower()

    def test_endpoint_health_check_failure(self):
        """
        Test that deployment handles endpoint health check failures
        """
        event = {
            'Records': [{
                'eventSource': 'aws:s3',
                's3': {
                    'bucket': {'name': 'test-bucket'},
                    'object': {'key': 'models/approved/model.tar.gz'}
                }
            }]
        }
        
        with patch.dict(os.environ, {
            'BUCKET_NAME': 'test-bucket',
            'SAGEMAKER_ROLE_ARN': 'arn:aws:iam::123456789012:role/SageMakerRole',
            'ENDPOINT_NAME': 'test-endpoint'
        }, clear=True):
            with patch('handler.sagemaker') as mock_sagemaker, \
                 patch('handler._validate_model_artifact') as mock_validate, \
                 patch('handler._verify_endpoint_health') as mock_health, \
                 patch('handler._rollback_deployment') as mock_rollback:
                
                # Setup mocks
                mock_validate.return_value = True
                mock_health.return_value = False  # Health check fails
                mock_sagemaker.describe_endpoint.side_effect = Exception("ResourceNotFound")
                
                context = Mock()
                result = handler.lambda_handler(event, context)
                
                # Should return error status
                assert result['statusCode'] == 500
                response_body = json.loads(result['body'])
                assert 'health check' in response_body['error'].lower()
                assert response_body['rollback_attempted'] == True
                
                # Verify rollback was attempted
                mock_rollback.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])