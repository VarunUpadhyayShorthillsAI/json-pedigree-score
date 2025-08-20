import os
import time
import pandas as pd
from ultralytics import YOLO

# ----------------------
# Training Configuration
# ----------------------
MODEL_NAME = "yolo11x.pt"
DATA_PATH = "/home/shorthills/projects/pedigree_vision/YOLO/Shaded-Nodes-4/data.yaml"  
EPOCHS = 200                     
BATCH_SIZE = 16
IMG_SIZE = 928
OUTPUT_EXCEL = "training_log.xlsx"

# ----------------------
# Load Model
# ----------------------
print(f"Starting training for model: {MODEL_NAME}")
model = YOLO(MODEL_NAME)


# Train

start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
print("Start time:", start_time)

results = model.train(
    data=DATA_PATH,
    epochs=200,          
    # patience=30,         # stop if val mAP50-95 doesn’t improve for 30 epochs
    batch=BATCH_SIZE,    
    imgsz=IMG_SIZE,
    device=0,
    deterministic=True,
    verbose=True,
    save=True,           # keep best/last
    save_period=-1,     
    project="Nodes-20-Aug",
    name="train_long",
)



# Collect Logs from results.csv
run_dir = results.save_dir  # YOLO auto-saves this run directory
csv_path = os.path.join(run_dir, "results.csv")

if os.path.exists(csv_path):
    df = pd.read_csv(csv_path)
    df.to_excel(OUTPUT_EXCEL, index=False)
    print(f"Training log saved to {OUTPUT_EXCEL}")
    print("Final Results:")
    print(df.tail(1))   # last epoch results
else:
    print("⚠️ results.csv not found. Check the YOLO run folder.")
