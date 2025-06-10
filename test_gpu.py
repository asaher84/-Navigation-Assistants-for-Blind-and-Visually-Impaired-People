import sys
import torch
import cv2
print("Python Version:", sys.version)
print("CUDA Available:", torch.cuda.is_available())
print("GPU Name:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU")
print("CUDA Device Count (OpenCV):", cv2.cuda.getCudaEnabledDeviceCount())