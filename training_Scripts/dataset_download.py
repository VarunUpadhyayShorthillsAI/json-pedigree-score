
from roboflow import Roboflow

print("Starting dataset download...")

try:
    rf = Roboflow(api_key="")
    project = rf.workspace("affected-nodes").project("affected-nodes")
    version = project.version(5)
    dataset = version.download("yolov5")
    
    print("✅ Dataset downloaded successfully!")
    
except Exception as e:
    print(f" Download failed: {e}")
    print("Check your API key and internet connection.")