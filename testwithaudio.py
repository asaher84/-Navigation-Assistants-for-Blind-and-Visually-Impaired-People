import cv2
from ultralytics import YOLO
from screeninfo import get_monitors
import pyttsx3  # Import the pyttsx3 library for text-to-speech

# Initialize the text-to-speech engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Adjust the speech rate (words per minute)

# Load the pre-trained YOLOv8 model (e.g., YOLOv8l - large version)
model = YOLO('yolov8l.pt')  # You can choose 'yolov8n.pt', 'yolov8s.pt', etc.

# Initialize webcam video capture
cap = cv2.VideoCapture(1)  # Use 0 for default camera. Change if you have multiple cameras.

if not cap.isOpened():
    print("Cannot open camera")
    exit()

# Create a named window with normal properties
cv2.namedWindow('YOLOv8 Real-Time Detection', cv2.WINDOW_NORMAL)

# Get the screen resolution
monitor = get_monitors()[0]
screen_width = monitor.width
screen_height = monitor.height

# Set the window size to the screen size
cv2.resizeWindow('YOLOv8 Real-Time Detection', screen_width, screen_height)

# Set the confidence threshold
CONFIDENCE_THRESHOLD = 0.7  # Adjust this value as needed

# Initialize a set to keep track of detected objects
detected_objects = set()

while True:
    # Capture frame-by-frame from the camera
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break

    # Perform object detection with the confidence threshold
    results = model(frame, conf=CONFIDENCE_THRESHOLD)

    # Visualize the results on the frame
    annotated_frame = results[0].plot()

    # Resize the frame to fit the screen resolution
    frame_resized = cv2.resize(annotated_frame, (screen_width, screen_height))

    # Display the resulting frame
    cv2.imshow('YOLOv8 Real-Time Detection', frame_resized)

    # Process detections and announce detected objects
    for result in results:
        for box in result.boxes:
            cls_id = int(box.cls[0])
            class_name = model.names[cls_id]
            confidence = box.conf[0]

            # Capitalize the first letter of the class name
            class_name_formatted = class_name.capitalize()

            # Check if the object has already been announced
            if class_name not in detected_objects:
                detected_objects.add(class_name)
                # Prepare and say the message
                message = f"{class_name_formatted} detected"
                print(message)  # Optional: Print the message to the console
                engine.say(message)
                engine.runAndWait()

    # Clear the set if no objects are detected to allow re-announcement
    if len(results[0].boxes) == 0:
        detected_objects.clear()

    # Press 'q' to exit the video stream
    if cv2.waitKey(1) == ord('q'):
        break

# When everything is done, release the capture and close windows
cap.release()
cv2.destroyAllWindows()
