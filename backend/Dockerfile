FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt
COPY backend /app/backend
COPY data /app/data
COPY frontend/dist /app/frontend/dist
ENV IDR_DATA_DIR=/app/backend/state IDR_THREADS=2
WORKDIR /app/backend
EXPOSE 8000
CMD ["python","-m","uvicorn","server:app","--host","0.0.0.0","--port","8000","--workers","1"]
