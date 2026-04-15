# Smart Blind Navigation Assistant

A real-time AI-powered navigation assistant designed to help visually impaired individuals move more safely and independently.  
The system uses computer vision and voice feedback to detect surroundings, identify obstacles, and guide users through live audio instructions.

## Features

- Real-time obstacle detection using webcam / camera feed
- Detects stairs, doors, vehicles, and nearby objects
- Voice-based alerts and navigation support
- Distance estimation for safer movement
- Lightweight and responsive interface
- Can be extended for outdoor and indoor navigation

## Tech Stack

- Python
- OpenCV
- YOLO / Deep Learning models
- FastAPI
- React
- Text-to-Speech APIs

## How It Works

The camera continuously captures the user's surroundings.  
A computer vision model processes each frame and detects important objects such as obstacles, pathways, stairs, or moving vehicles.  
Based on the detected environment, the system gives voice alerts like:

- "Obstacle ahead"
- "Stairs on the left"
- "Path is clear"

This helps the user understand their surroundings without needing visual input.

