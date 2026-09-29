# IntelliDr
## AI/ML-Based Intelligent Dead Reckoning System for GNSS-Denied Navigation

IntelliDr is an AI/ML-powered navigation system designed to provide continuous vehicle navigation during GNSS/GPS signal outages.

The system uses smartphone Inertial Measurement Unit (IMU) data, including accelerometer and gyroscope measurements, to estimate vehicle motion and speed. A temporal deep-learning model analyzes the sensor data and provides speed estimates that are subsequently used by the inertial navigation and sensor-fusion pipeline.

The system is designed for challenging environments such as:

- Tunnels
- Dense urban environments
- Underground parking areas
- GNSS-denied environments
- Temporary GNSS signal outages

---

# Problem Statement

Modern navigation systems heavily depend on GNSS/GPS signals.

However, GNSS signals can become unavailable or unreliable due to:

- Signal blockage
- Tunnels
- Buildings and urban canyons
- Underground environments
- Atmospheric interference
- Intentional or accidental signal disruption

When GNSS becomes unavailable, conventional navigation systems can lose accurate positioning.

### The Objective of IntelliDr

> Estimate vehicle movement and maintain navigation using onboard smartphone sensors when GNSS is temporarily unavailable.

---

# How IntelliDr Works

The complete system can be represented as:

```text
                 GNSS AVAILABLE
                       |
                       v
                 Initial Position
                       |
                       v
              +-----------------+
              |   Smartphone    |
              |      IMU        |
              +--------+--------+
                       |
              Accelerometer
                       +
                  Gyroscope
                       |
                       v
              +-----------------+
              | Data Processing |
              +--------+--------+
                       |
                       v
              +-----------------+
              |   TCN AI Model  |
              |                 |
              | Speed Estimation|
              +--------+--------+
                       |
                 Speed + Uncertainty
                       |
                       v
              +-----------------+
              | Inertial        |
              | Navigation /    |
              | Sensor Fusion   |
              +--------+--------+
                       |
                       v
              Estimated Position
                       |
                       v
              +-----------------+
              |  Map Matching   |
              +--------+--------+
                       |
                       v
              Corrected Position
                       |
                       v
                   Navigation
```

---

# 1. IMU Data Collection

The smartphone's Inertial Measurement Unit (IMU) provides continuous motion information.

The system primarily uses:

## Accelerometer

Measures acceleration along three axes:

```text
Ax
Ay
Az
```

## Gyroscope

Measures rotational movement:

```text
Gx
Gy
Gz
```

Together, these provide a six-dimensional representation of the vehicle's motion:

```text
[Ax, Ay, Az, Gx, Gy, Gz]
```

---

# 2. Data Processing

Raw IMU data contains noise caused by:

- Road vibrations
- Potholes
- Phone movement
- Sensor noise
- Vehicle acceleration and braking
- Irregular driving conditions

The incoming sensor data is therefore processed and organized into time-based windows before being passed to the AI model.

The model analyzes a sequence of sensor observations rather than relying on a single sensor reading.

---

# 3. TCN-Based Speed Estimation

The core AI component uses a Temporal Convolutional Network (TCN).

TCN is particularly suitable for this problem because IMU data is a time-series signal.

Instead of asking:

> "What does this single sensor reading mean?"

the model asks:

> "What does this sequence of sensor readings over time tell us about the vehicle's motion?"

The model analyzes a short window of IMU measurements and learns patterns associated with vehicle movement.

## Input

```text
Ax
Ay
Az
Gx
Gy
Gz
```

across multiple time steps.

## Output

The model estimates:

```text
Vehicle Speed
+
Prediction Uncertainty
```

The uncertainty estimate is useful because sensor measurements can become less reliable during events such as heavy vibration or potholes.

---

# 4. Temporal Window

The model works with a sequence of sensor observations instead of isolated readings.

For example:

```text
Time →

t1   t2   t3   t4   t5   ...   t35
|    |    |    |    |          |
IMU  IMU  IMU  IMU  IMU  ...   IMU
```

This allows the model to recognize patterns such as:

## Acceleration

```text
0.2 -> 0.4 -> 0.7 -> 1.0 -> 1.3
```

## Braking

```text
1.0 -> 0.7 -> 0.3 -> -0.2 -> -0.8
```

## Vibration / Noise

```text
0.2 -> 2.8 -> 0.4 -> 3.1 -> 0.1
```

The temporal model learns to distinguish these patterns and estimate the vehicle's motion.

---

# 5. Inertial Navigation

Once the AI estimates vehicle speed, the information is passed to the navigation pipeline.

The system combines:

```text
Previous Position
+
Estimated Speed
+
Vehicle Orientation
+
IMU Measurements
```

to estimate the next position.

Conceptually:

```text
Previous Position
       |
       v
Vehicle Motion
       |
       v
Distance Travelled
       |
       v
New Estimated Position
```

This allows navigation to continue even when GNSS is unavailable.

---

# 6. GNSS + INS Fusion

When GNSS is available, GNSS measurements can provide an external position reference.

The system can combine GNSS information with inertial measurements:

```text
GNSS -------------+
                  |
                  v
                Fusion
                  ^
                  |
IMU --------------+
```

GNSS provides an absolute position reference, while IMU provides continuous motion information.

When GNSS becomes unavailable, the inertial
# 21. Local Setup and Running the Backend

The IntelliDr backend can be run locally using Python and FastAPI.

## Prerequisites

Install the following:

- Python 3.x
- Git
- VS Code
- MongoDB, if the local configuration requires database connectivity

---

## Step 1: Open the Project

Open the IntelliDr backend folder in VS Code.

Then open the VS Code terminal or Windows Command Prompt.

Navigate to the project directory:

```bash
cd path\to\dead-reckoning
```

For example:

```bash
cd Downloads\dead-reckoning
```

---

## Step 2: Create a Virtual Environment

Create a Python virtual environment:

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

After activation, the terminal should show something similar to:

```text
(venv) C:\Users\Username\Downloads\dead-reckoning>
```

The virtual environment keeps the project's Python packages separate from the rest of the system.

---

## Step 3: Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

This installs the libraries required by the backend, including the FastAPI and machine-learning dependencies specified by the project.

---

## Step 4: Configure Environment Variables

Create or configure the `.env` file in the backend/project directory.

Example:

```env
MONGO_URL=your_mongodb_connection_string
```

Other environment variables can be added depending on the project configuration.

Do not upload sensitive credentials or private connection strings to GitHub.

---

## Step 5: Start the FastAPI Server

Run the backend using Uvicorn:

```bash
uvicorn server:app --reload
```

If the server file is located differently, use the corresponding module path.

For example:

```bash
uvicorn backend.server:app --reload
```

The terminal should display something similar to:

```text
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

---

## Step 6: Open the Backend

Once the server is running, open:

```text
http://127.0.0.1:8000
```

The FastAPI application can then be accessed locally.

---

## Step 7: Open FastAPI Documentation

FastAPI automatically provides interactive API documentation.

Open:

```text
http://127.0.0.1:8000/docs
```

This provides a Swagger interface where available API endpoints can be viewed and tested.

The interface can be used to:

- View available endpoints
- Send API requests
- Upload or provide data
- Test model-related endpoints
- View API responses

---

# Running the Complete Backend

The basic CMD workflow is:

```bash
cd path\to\dead-reckoning

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

uvicorn server:app --reload
```

Then open:

```text
http://127.0.0.1:8000
```

or:

```text
http://127.0.0.1:8000/docs
```

---

# Running the Frontend and Backend Together

If the project contains a separate React frontend, the backend and frontend are run as separate processes.

### Terminal 1: Backend

```bash
cd backend
venv\Scripts\activate
uvicorn server:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

### Terminal 2: Frontend

Open another terminal and navigate to the frontend:

```bash
cd frontend
```

Install the JavaScript dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

The frontend communicates with the FastAPI backend through HTTP API requests.

```text
React Frontend
      |
      | HTTP Requests
      v
FastAPI Backend
      |
      v
ML / Processing / Database
```

---

# Running the Deployed Version

The backend is also deployed online using Render.

Live backend:

```text
https://final-dead-reckoning.onrender.com/
```

The deployed architecture is:

```text
User / Frontend
       |
       | HTTP Request
       v
Render
       |
       v
FastAPI Backend
       |
       +---- Data Processing
       |
       +---- ML Model
       |
       +---- Navigation
       |
       +---- Database
       |
       v
API Response
```

The local version is useful for development and testing, while the Render deployment provides a publicly accessible backend.

---

# Quick CMD Reference

```bash
# Navigate to project
cd path\to\dead-reckoning

# Create virtual environment
python -m venv venv

# Activate environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run FastAPI
uvicorn server:app --reload
```

Then visit:

```text
http://127.0.0.1:8000
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

Deployed backend:

```text
https://final-dead-reckoning.onrender.com/
```
