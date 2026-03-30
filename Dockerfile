# Stage 1: build React frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_API_URL=""
ARG VITE_WEBHOOK_SECRET=""
RUN --mount=type=secret,id=VITE_WEBHOOK_SECRET \
    VITE_WEBHOOK_SECRET=$(cat /run/secrets/VITE_WEBHOOK_SECRET 2>/dev/null || echo "$VITE_WEBHOOK_SECRET") \
    npm run build

# Stage 2: Python backend + serve built frontend
FROM python:3.12-slim

WORKDIR /app

# Install system deps for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Mount built frontend as static files from FastAPI
COPY docker_entrypoint.py ./

# Hugging Face Spaces requires port 7860
ENV PORT=7860
EXPOSE 7860

CMD ["python", "docker_entrypoint.py"]
