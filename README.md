# Virtual Painter using Hand Gestures

A Python application that allows you to draw on your screen using hand gestures detected through your webcam.

## Features

- **Hand Tracking**: Uses MediaPipe to detect hand landmarks in real-time
- **Drawing**: Draw by moving your index finger
- **Color Selection**: 
  - Click on color buttons at the top of the screen
  - Use two-finger gesture to cycle through colors
- **Eraser Mode**: Toggle eraser to clear parts of your drawing
- **Clear Canvas**: Show open palm and press 'c' to clear the entire canvas
- **Smooth Drawing**: Lines are smoothed to prevent breaking

## Installation

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
python main.py
```

## Usage Instructions

### Drawing
- **Draw**: Raise only your index finger and move it around
- **Stop Drawing**: Lower your index finger or raise additional fingers

### Color Selection
- **Click Buttons**: Point your index finger at color buttons at the top
- **Gesture Control**: Raise both index and middle fingers to cycle through colors

### Eraser
- **Toggle Eraser**: Click the gray "ERASER" button
- **Use Eraser**: Move your index finger while in eraser mode

### Clear Canvas
- **Show Palm**: Open your hand with all fingers extended
- **Confirm**: Press 'c' to clear or any other key to cancel

### Exit
- Press 'q' to quit the application

## Controls Summary
- **Index finger only**: Drawing mode
- **Index + Middle fingers**: Cycle colors
- **Any 3 fingers**: Cycle colors
- **Open palm**: Clear canvas prompt
- **'q'**: Quit application
- **'c'**: Confirm clear canvas

## Technical Details
- Uses OpenCV for video processing and UI
- MediaPipe for hand landmark detection
- Smoothing algorithm for better drawing experience
- Modular code structure for easy maintenance
