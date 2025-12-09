from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import os
import tarfile

MODEL = "distilbert-base-cased"

tokenizer = AutoTokenizer.from_pretrained(MODEL)
model = AutoModelForSequenceClassification.from_pretrained(MODEL)

os.makedirs("model", exist_ok=True)
model.save_pretrained("model")
tokenizer.save_pretrained("model")

# Create tar file
with tarfile.open("model.tar.gz", "w:gz") as tar:
    tar.add("model", arcname=".")
