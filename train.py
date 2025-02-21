import ultralytics
from ultralytics import YOLO

# Parameters for training
DATA_YAML = r'D:\Ashutosh\blind\project\Housing Data.v2-version-2.yolov8\data.yaml'  # Replace with your dataset.yaml path
MODEL_NAME = 'yolov8n.pt'  # YOLOv8 pre-trained model name (e.g. yolov8n.pt)
EPOCHS = 100  # Number of training epochs
BATCH_SIZE = 16  # Batch size for training
IMG_SIZE = 640  # Image size for training
DEVICE = 'cpu'  # Device to use for training (e.g. "cpu" or "0" for GPU)

# Load the model (YOLOv8)
model = YOLO(MODEL_NAME)

# Train the model
model.train(
    data=DATA_YAML,
    epochs=EPOCHS,
    batch=BATCH_SIZE,
    imgsz=IMG_SIZE,
    device=DEVICE
)
