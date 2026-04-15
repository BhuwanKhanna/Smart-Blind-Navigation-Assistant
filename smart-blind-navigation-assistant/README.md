# Smart AI Blind Navigation Assistant

A production-style internship portfolio project that turns a webcam or mobile camera into a real-time navigation guide for visually impaired users. The system detects obstacles, vehicles, doors, stairs, pathways, and sudden hazards, estimates distance, and provides instant voice instructions such as "step left" or "vehicle approaching".

## Highlights

- Real-time camera pipeline with OpenCV and YOLO-ready object detection
- Offline-friendly fallback detection logic when YOLO weights are unavailable
- Monocular distance estimation using class-aware width priors
- Live voice guidance with multilingual text-to-speech
- Direction arrows and annotated live feed
- Emergency alert button and location sharing simulation
- Hazard confidence scoring, activity log, and alert history
- FastAPI backend and Streamlit dashboard with accessible dark UI
- Docker-ready structure for deployment demos

## Tech stack

- Python
- OpenCV
- FastAPI
- Streamlit
- YOLO via `ultralytics` when installed
- Offline text-to-speech via `pyttsx3`
- SQLite for persistent event logging

## Project structure

```text
smart-blind-navigation-assistant/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   └── services/
│   ├── artifacts/
│   └── Dockerfile
├── dashboard/
│   ├── components/
│   └── Dockerfile
├── .env.example
├── docker-compose.yml
├── requirements.txt
└── requirements-ml.txt
```

## Core features

- Detects:
  - Obstacles
  - Vehicles
  - Doors
  - Stairs
  - Clear pathways
  - Sudden hazards and approaching objects
- Speaks guidance in English, Hindi, or Spanish
- Estimates distance to the most relevant hazard
- Simulates guardian alerting and location sharing
- Logs navigation events for dashboard review and CSV export

## Local setup

1. Create a virtual environment.
2. Install base dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install optional ML extras for YOLO:

   ```bash
   pip install -r requirements-ml.txt
   ```

4. Copy `.env.example` to `.env`.
5. Start the backend:

   ```bash
   uvicorn backend.app.main:app --reload --port 8000
   ```

6. Start the dashboard:

   ```bash
   streamlit run dashboard/app.py
   ```

## Demo mode behavior

- If `ultralytics` is not available, the app falls back to OpenCV-based scene heuristics.
- If offline voice cannot initialize, guidance text is still generated and shown in the dashboard.
- If SMS or email credentials are missing, alerts are safely simulated and still logged.

## Accessibility notes

- Large controls and high-contrast dark theme
- Voice guidance rate controls
- Multilingual guidance output
- Offline-capable local speech engine

## Portfolio value

- Real-time assistive AI product design
- Vision pipeline, distance estimation, and hazard scoring
- Human-centered accessibility engineering
- End-to-end backend, dashboard, deployment, and demo simulation workflow
