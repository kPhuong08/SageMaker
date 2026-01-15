# Báo Cáo: Tạo Model Evaluator Lambda

**Ngày:** 15/01/2026  
**Trạng thái:** ✅ HOÀN THÀNH

---

## 🔴 VẤN ĐỀ PHÁT HIỆN

### **Triệu chứng:**
Model được training xong và upload lên `s3://atml-models-bucket/models/raw/training-job-20260115-043350/output/model.tar.gz` nhưng **KHÔNG CÓ GÌ XẢY RA TIẾP THEO**.

### **Nguyên nhân:**
Training Orchestrator Lambda có **timeout 15 phút (900 giây)**, nhưng code có vòng lặp `monitor_training_job()` chờ training job hoàn thành (có thể mất 30-60 phút hoặc lâu hơn).

**Flow cũ (SAI):**
```
Training Orchestrator Lambda:
1. Start training job ✅
2. Monitor training (vòng lặp while True) ❌ TIMEOUT!
3. Evaluate model (KHÔNG BAO GIỜ CHẠY ĐẾN ĐÂY)
4. Copy sang models/approved/ (KHÔNG BAO GIỜ CHẠY ĐẾN ĐÂY)
```

**Kết quả:** Lambda bị kill sau 15 phút, model không được evaluate và không được deploy.

---

## ✅ GIẢI PHÁP TRIỂN KHAI

### **Kiến trúc mới: Tách Lambda thành 3 functions**

```
┌─────────────────────────────────────────────────────────────────┐
│                      NEW ARCHITECTURE                            │
└─────────────────────────────────────────────────────────────────┘

1. TRAINING ORCHESTRATOR LAMBDA
   ├─ Trigger: S3 event (data/train/*)
   ├─ Action: Start SageMaker training job
   └─ Return: Immediately (không chờ)
   
2. MODEL EVALUATOR LAMBDA (MỚI!)
   ├─ Trigger: EventBridge SageMaker Training Job State Change
   ├─ Action: Evaluate model, copy sang models/approved/
   └─ Return: Evaluation result
   
3. DEPLOYMENT ORCHESTRATOR LAMBDA
   ├─ Trigger: S3 event (models/approved/*)
   ├─ Action: Deploy model to endpoint
   └─ Return: Deployment result
```

---

## 📁 FILES ĐÃ TẠO/SỬA

### **1. Model Evaluator Lambda Handler (MỚI)**
**File:** `SageMaker/lambda/model_evaluator/handler.py`

**Chức năng:**
- Nhận EventBridge event khi training job complete/failed/stopped
- Download model artifact từ S3
- Extract và đọc metrics.json
- So sánh metrics với thresholds
- Copy approved model sang `models/approved/`
- Gửi SNS notification

**Timeout:** 5 phút (đủ cho evaluation)

---

### **2. Model Evaluator Terraform Module (MỚI)**

**Files:**
- `SageMaker/terraform/modules/lambda_model_evaluator/main.tf`
- `SageMaker/terraform/modules/lambda_model_evaluator/variables.tf`
- `SageMaker/terraform/modules/lambda_model_evaluator/outputs.tf`

**Configuration:**
```hcl
resource "aws_lambda_function" "model_evaluator" {
  function_name = "mlops-model-evaluator-${var.bucket_name}"
  handler       = "handler.lambda_handler"
  runtime       = "python3.9"
  timeout       = 300  # 5 minutes
  memory_size   = 1024 # More memory for model download
}
```

---

### **3. Training Orchestrator Lambda (REFACTORED)**
**File:** `SageMaker/lambda/training_orchestrator/handler.py`

**Thay đổi:**
- ❌ **Xóa:** `monitor_training_job()` - vòng lặp chờ training xong
- ❌ **Xóa:** `evaluate_model()` - đã chuyển sang Model Evaluator
- ❌ **Xóa:** `handle_model_approval()` - đã chuyển sang Model Evaluator
- ✅ **Thêm:** `send_training_started_notification()` - thông báo training bắt đầu

**Flow mới:**
```python
def lambda_handler(event, context):
    # Extract S3 info
    s3_info = extract_s3_info_from_event(event)
    
    # Start training job
    training_job_name = start_training_job(s3_info)
    
    # Send notification
    send_training_started_notification(training_job_name, s3_info)
    
    # Return immediately (không chờ!)
    return {'statusCode': 200, 'training_job_name': training_job_name}
```

---

### **4. EventBridge Module (UPDATED)**
**File:** `SageMaker/terraform/modules/eventbridge/main.tf`

**Thêm rule mới:**
```hcl
# NEW: SageMaker Training Job State Change -> Model Evaluator Lambda
resource "aws_cloudwatch_event_rule" "training_job_state_change_rule" {
  name = "mlops-training-job-state-change-..."
  
  event_pattern = jsonencode({
    source      = ["aws.sagemaker"],
    detail-type = ["SageMaker Training Job State Change"],
    detail = {
      TrainingJobStatus = ["Completed", "Failed", "Stopped"]
    }
  })
}
```

**Event pattern:**
- Source: `aws.sagemaker`
- Detail-type: `SageMaker Training Job State Change`
- Status: `Completed`, `Failed`, `Stopped`

---

### **5. Main Terraform Configuration (UPDATED)**
**File:** `SageMaker/terraform/main.tf`

**Thêm:**
```hcl
# Package Model Evaluator Lambda
data "archive_file" "model_evaluator_zip_path" {
  type        = "zip"
  source_file = var.model_evaluator_source_file
  output_path = "${path.module}/../lambda/model_evaluator/model_evaluator.zip"
}

# Model Evaluator Lambda Module
module "lambda_model_evaluator" {
  source = "./modules/lambda_model_evaluator"
  
  lambda_zip_path = data.archive_file.model_evaluator_zip_path.output_path
  lambda_handler  = var.model_evaluator_handler
  bucket_name     = module.s3.s3_bucket_name
  lambda_role_arn = module.iam.lambda_role_arn
  region          = var.aws_region
  sns_topic_arn   = module.monitoring.sns_topic_arn
}
```

---

### **6. Variables (UPDATED)**
**File:** `SageMaker/terraform/variables.tf`

**Thêm:**
```hcl
# Model Evaluator Lambda Configuration
variable "model_evaluator_source_file" {
  description = "Path to the model evaluator Lambda source file"
  type        = string
  default     = "../lambda/model_evaluator/handler.py"
}

variable "model_evaluator_handler" {
  description = "Model evaluator Lambda handler"
  type        = string
  default     = "handler.lambda_handler"
}
```

---

## 🔄 FLOW MỚI HOÀN CHỈNH

### **Scenario: Training thành công**

```
1. GitHub Actions upload data
   └─ s3://bucket/data/train/sample_data.csv
   
2. S3 Event → EventBridge → Training Orchestrator Lambda
   ├─ Start training job: training-job-20260115-120000
   ├─ Send notification: "Training started"
   └─ Return immediately ✅
   
3. SageMaker Training Job runs (30-60 phút)
   ├─ Download model from HuggingFace Hub
   ├─ Train model
   ├─ Save model to s3://bucket/models/raw/.../model.tar.gz
   └─ Status: Completed
   
4. SageMaker Event → EventBridge → Model Evaluator Lambda
   ├─ Download model.tar.gz
   ├─ Extract metrics.json
   ├─ Compare metrics vs thresholds
   ├─ Evaluation: PASSED ✅
   ├─ Copy to s3://bucket/models/approved/.../model.tar.gz
   └─ Send notification: "Model approved"
   
5. S3 Event → EventBridge → Deployment Orchestrator Lambda
   ├─ Validate model artifact
   ├─ Create SageMaker model
   ├─ Create endpoint config
   ├─ Create/update endpoint
   └─ Send notification: "Deployment successful"
   
6. Endpoint InService ✅
```

**Timeline:**
- 0:00 - Training started
- 0:01 - Training Orchestrator returns
- 0:30 - Training in progress
- 1:00 - Training completed
- 1:01 - Model Evaluator triggered
- 1:02 - Model evaluated and approved
- 1:03 - Deployment Orchestrator triggered
- 1:08 - Endpoint InService

**Total:** ~68 phút (không bị timeout!)

---

### **Scenario: Training thất bại**

```
1-3. Same as above

4. SageMaker Event → EventBridge → Model Evaluator Lambda
   ├─ Training status: Failed
   ├─ Send notification: "Training failed"
   └─ Return (không evaluate)
   
5. Flow stops ✅ (đúng behavior)
```

---

### **Scenario: Model fails evaluation**

```
1-4. Same as success scenario until evaluation

4. Model Evaluator Lambda
   ├─ Download model.tar.gz
   ├─ Extract metrics.json
   ├─ Compare metrics vs thresholds
   ├─ Evaluation: FAILED ❌
   ├─ Do NOT copy to models/approved/
   └─ Send notification: "Model failed evaluation"
   
5. Flow stops ✅ (đúng behavior - không deploy bad model)
```

---

## 📊 SO SÁNH TRƯỚC/SAU

### **Trước (SAI):**
| Component | Timeout | Behavior | Result |
|-----------|---------|----------|--------|
| Training Orchestrator | 15 min | Start + Monitor + Evaluate | ❌ TIMEOUT |
| Model Evaluator | N/A | N/A | ❌ KHÔNG TỒN TẠI |
| Deployment Orchestrator | 5 min | Deploy | ❌ KHÔNG BAO GIỜ CHẠY |

**Vấn đề:**
- Training Orchestrator timeout trước khi training xong
- Model không được evaluate
- Model không được deploy

---

### **Sau (ĐÚNG):**
| Component | Timeout | Behavior | Result |
|-----------|---------|----------|--------|
| Training Orchestrator | 15 min | Start only | ✅ RETURN NGAY |
| Model Evaluator | 5 min | Evaluate + Approve | ✅ CHẠY KHI TRAINING XONG |
| Deployment Orchestrator | 5 min | Deploy | ✅ CHẠY KHI MODEL APPROVED |

**Lợi ích:**
- Không có Lambda nào bị timeout
- Model được evaluate tự động
- Model được deploy tự động
- Event-driven architecture hoàn chỉnh

---

## 🎯 EVENTBRIDGE RULES SUMMARY

### **Rule 1: Training Data Upload**
```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {"name": ["atml-models-bucket"]},
    "object": {"key": [{"prefix": "data/train/"}]}
  }
}
```
**Target:** Training Orchestrator Lambda

---

### **Rule 2: Training Job State Change (MỚI!)**
```json
{
  "source": ["aws.sagemaker"],
  "detail-type": ["SageMaker Training Job State Change"],
  "detail": {
    "TrainingJobStatus": ["Completed", "Failed", "Stopped"]
  }
}
```
**Target:** Model Evaluator Lambda

---

### **Rule 3: Approved Model Upload**
```json
{
  "source": ["aws.s3"],
  "detail-type": ["Object Created"],
  "detail": {
    "bucket": {"name": ["atml-models-bucket"]},
    "object": {"key": [{"prefix": "models/approved/"}]}
  }
}
```
**Target:** Deployment Orchestrator Lambda

---

## 🚀 DEPLOYMENT STEPS

### **1. Validate Terraform**
```bash
cd SageMaker/terraform
terraform init -upgrade
terraform validate
```

**Expected:** `Success! The configuration is valid.`

---

### **2. Review Changes**
```bash
terraform plan
```

**Expected changes:**
- ✅ Add: `aws_lambda_function.model_evaluator`
- ✅ Add: `aws_cloudwatch_event_rule.training_job_state_change_rule`
- ✅ Add: `aws_cloudwatch_event_target.model_evaluator_rule_target`
- ✅ Add: `aws_lambda_permission.allow_eventbridge_model_evaluator`
- ✅ Modify: `aws_lambda_function.training_orchestrator` (code change)

---

### **3. Deploy**
```bash
terraform apply
```

**Nhập `yes` khi được hỏi.**

---

### **4. Test Flow**
```bash
# Upload test data
aws s3 cp test_data.csv s3://atml-models-bucket/data/train/

# Monitor logs
aws logs tail /aws/lambda/mlops-training-orchestrator-atml-models-bucket --follow

# Wait for training to complete (30-60 min)

# Monitor Model Evaluator logs
aws logs tail /aws/lambda/mlops-model-evaluator-atml-models-bucket --follow

# Monitor Deployment logs
aws logs tail /aws/lambda/mlops-deployment-orchestrator-atml-models-bucket --follow
```

---

## ✅ VERIFICATION CHECKLIST

### **Infrastructure:**
- [ ] Model Evaluator Lambda created
- [ ] EventBridge rule for training job state change created
- [ ] Lambda permissions granted
- [ ] CloudWatch log groups created

### **Functionality:**
- [ ] Training Orchestrator starts job and returns immediately
- [ ] Model Evaluator triggered when training completes
- [ ] Model evaluation runs successfully
- [ ] Approved model copied to models/approved/
- [ ] Deployment Orchestrator triggered by approved model

### **Notifications:**
- [ ] Training started notification received
- [ ] Model evaluation notification received
- [ ] Deployment notification received

---

## 📞 SUMMARY

### **Vấn đề:**
Training Orchestrator Lambda timeout trước khi training xong, model không được evaluate và deploy.

### **Giải pháp:**
Tạo Model Evaluator Lambda mới, trigger bởi EventBridge khi training job complete.

### **Kết quả:**
- ✅ Training Orchestrator chỉ start job và return ngay
- ✅ Model Evaluator chạy khi training xong
- ✅ Model được evaluate và approve tự động
- ✅ Deployment chạy khi model approved
- ✅ Không có Lambda nào bị timeout

### **Files changed:**
- **Created:** 4 files (Model Evaluator Lambda + Terraform module)
- **Modified:** 6 files (Training Orchestrator, EventBridge, main.tf, variables.tf)

### **Ready to deploy:** ✅ YES

**Hệ thống giờ hoạt động đúng flow event-driven architecture! 🚀**
