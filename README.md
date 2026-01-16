# 🚀 SageMaker MLOps - Event-Driven ML Training & Deployment

**Hệ thống MLOps tự động hóa cho training DistilBERT + serverless inference trên AWS**

## ⚡ Quick Start

```bash
# 1. Initialize infrastructure
cd SageMaker/terraform
terraform init
terraform apply

# 2. Upload training data (triggers everything)
aws s3 cp data.csv s3://atml-models-bucket/data/train/

# 3. Pipeline runs automatically:
# - Training starts → Model evaluated → If passed, endpoint deployed ✅
```

## 🎯 Hệ Thống Hoạt Động

| Step | Component | Action |
|------|-----------|--------|
| 1️⃣ | S3 Event | Data uploaded → triggers EventBridge |
| 2️⃣ | Training Lambda | Starts SageMaker training job |
| 3️⃣ | SageMaker | Fine-tunes DistilBERT + compute metrics |
| 4️⃣ | Evaluation | Compare metrics vs thresholds |
| 5️⃣ | IF PASS | Upload to `models/approved/` |
| 6️⃣ | Deployment Lambda | Create/update serverless endpoint |
| 7️⃣ | Ready | Endpoint ready for inference ✅ |

## 📁 Project Structure

```
.
├── SageMaker/
│   ├── README.md                    # Detailed documentation (1244 lines)
│   ├── huggingface/
│   │   ├── src/train.py             # Training script with fine-tuning
│   │   ├── ops/evaluate_model.py    # Model evaluation logic
│   │   └── ops/prepare_data.py      # Data preprocessing
│   ├── lambda/
│   │   ├── training_orchestrator/   # Orchestrate training pipeline
│   │   └── deployment_orchestrator/ # Deploy to serverless endpoint
│   ├── terraform/                   # Infrastructure as Code (AWS resources)
│   ├── config/
│   │   └── evaluation_thresholds.json  # Model quality thresholds
│   └── examples/
│       └── sample_data.csv          # Sample training data
├── tests/                           # Unit tests
└── .github/workflows/               # CI/CD pipeline
```

## 🔧 Key Features

- ✅ **Event-Driven**: Auto-triggers on S3 data upload
- ✅ **Fully Automated**: Training → Evaluation → Deployment
- ✅ **Serverless**: Pay only for what you use
- ✅ **Infrastructure as Code**: Reproducible with Terraform
- ✅ **Monitoring**: CloudWatch metrics, SNS notifications
- ✅ **Easy Inference**: REST API to pre-trained endpoint

## 📊 Data Format

**CSV with columns: `text`, `label`**
```csv
text,label
"Amazing product!",1
"Bad quality.",0
```

## 🚀 Deploy

```bash
# 1. AWS CLI configured
aws configure

# 2. Setup infrastructure (20 minutes)
cd SageMaker/terraform
terraform apply

# 3. Upload data
aws s3 cp data.csv s3://atml-models-bucket/data/train/

# 4. Monitor
aws logs tail /aws/lambda/training-orchestrator --follow
```

## 🔍 Monitor Training

```bash
# Check training logs
aws logs tail /aws/lambda/training-orchestrator --follow

# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name serverless-inference-endpoint
```

## 🤖 Make Predictions

```python
import boto3, json

client = boto3.client('sagemaker-runtime')
response = client.invoke_endpoint(
    EndpointName='serverless-inference-endpoint',
    ContentType='application/json',
    Body=json.dumps({"inputs": "Great product!"})
)
print(json.loads(response['Body'].read()))
```

## 📖 Full Documentation

👉 **[SageMaker/README.md](SageMaker/README.md)** - Detailed architecture, all components, troubleshooting

## ⚙️ Configuration

- **Training model**: `distilbert-base-cased`
- **Instance type**: `ml.m5.xlarge`
- **Endpoint memory**: `3072 MB` (serverless)
- **Evaluation thresholds**: See `SageMaker/config/evaluation_thresholds.json`

## 📝 Thay Đổi Gần Đây

- ✅ Fixed metrics = 0.0 (auto train/test split)
- ✅ Fixed import errors (sklearn imports at top)
- ✅ Updated to distilbert-base-cased
- ✅ Fixed deployment validation (model name length)
- ✅ All tests passing

## 🔐 Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured
- Terraform installed
- 500+ training examples (recommended)

---

**Status**: Production Ready ✅ | **Last Updated**: Jan 16, 2026
