from ultralytics import YOLO
import cv2

# Create a new YOLO model from scratch
# Using v8 bc good for beginners and good Python API
model = YOLO("yolov8n.pt")

# What to train on? Custom dataset?
# Use a real-world dataset as your primary training base 
# Fine-tune on Gazebo-rendered images
# Apply domain randomization in Gazebo s

results = model.predict('apple.jpg') # model prediction on apple test image

# inspect results
for result in results:
    boxes = result.boxes
    for box in boxes:
        xyxy = box.xyxy[0]      # bounding box corners [x1, y1, x2, y2]
        conf = box.conf[0]      # confidence score
        cls  = box.cls[0]       # class ID
        name = model.names[int(cls)]  # class name string
        print(f"{name}: {conf:.2f} @ {xyxy}")


results = model.predict('apple_banana.jpg') # model prediction on apple and banana test image

img = cv2.imread('apple_banana.jpg')

# inspect results
for result in results:
    boxes = result.boxes
    for box in boxes:
        xyxy = box.xyxy[0]      # bounding box corners [x1, y1, x2, y2]
        conf = box.conf[0]      # confidence score
        cls  = box.cls[0]       # class ID
        name = model.names[int(cls)]  # class name string
        print(f"{name}: {conf:.2f} @ {xyxy}")

        x1, y1, x2, y2 = map(int, xyxy)
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)

cv2.imshow('bounding box', img)
cv2.waitKey(0)
cv2.destroyAllWindows()