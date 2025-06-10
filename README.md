
# Blind Navigation System with Voice-Controlled Object Detection

This project provides a computer vision-based assistive system designed to help visually impaired users navigate their environment. It features real-time object detection with voice command interaction and two operation modes: **Normal Mode** (announces detected objects) and **Find Mode** (tracks and locates specific object types like "person").

## Features

- 🎤 **Voice Commands**: Trigger mode changes by saying "Hello system", "Find mode on", or "Normal mode on".
- 🎥 **Live Object Detection**: Detect and track objects in real-time using webcam or video feed.
- 🧠 **Dual Modes**:
  - **Normal Mode**: Detects multiple object classes and announces them.
  - **Find Mode**: Focuses on locating a specific object type (e.g., person).
- 🖥️ **Full-Screen UI**: Adjustable to screen resolution for immersive view.

## Folder Structure

```
.
├── caller.py                # Main launcher with mode switching and UI
├── caller_ui.py             # Enhanced full-screen version
├── speech_monitor.py        # Lightweight variant with reduced retries
├── test_gpu.py              # GPU check utility
└── Base/
    ├── detect.py            # Object detection logic
    └── detect_track.py      # Object tracking logic
```

## Installation

1. **Clone the repository**:

```bash
git clone https://github.com/yourusername/blind-navigation.git
cd blind-navigation
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

You may need the following Python packages:
- `opencv-python`
- `torch` and `torchvision`
- `speechrecognition`
- `pyaudio`
- `screeninfo` (for fullscreen UI mode)

3. **(Optional) Test GPU availability**:

```bash
python test_gpu.py
```

## Usage

To run the system:

```bash
python caller.py
```

Or for fullscreen interface (recommended):

```bash
python caller_ui.py
```

To use the voice commands:
- Say **"Hello system"** to interact.
- Follow up with **"Find mode on"** or **"Normal mode on"**.

## Notes

- Ensure your microphone is configured and working.
- Webcam or video input device must be available.
- Modify `video_source` in `caller_ui.py` if using an external camera or video file.

## License

This project is licensed under the MIT License.
