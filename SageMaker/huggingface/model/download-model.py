from huggingface_hub import snapshot_download
import os
import shutil

# Tên model trên Hugging Face Hub 
MODEL_ID = "distilbert-base-cased" 

# Thư mục sẽ đóng gói để upload
OUTPUT_DIR = "./model_package"

def prepare_model():
    # 1. Tạo thư mục sạch
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR)

    # 2. Tải model về thư mục này
    print(f"Downloading {MODEL_ID}...")
    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=OUTPUT_DIR,
        local_dir_use_symlinks=False, # Quan trọng: Để lấy file thật, không lấy shortcut
        ignore_patterns=["*.msgpack", "*.h5"] # Bỏ qua các file không cần thiết cho PyTorch
    )
    print(" Download Completed!")

if __name__ == "__main__":
    prepare_model()