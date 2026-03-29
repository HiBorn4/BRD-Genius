FROM python:3.11-slim

# Install system dependencies for audio/video processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create middleware directory for local storage mode
RUN mkdir -p app_files/middleware

EXPOSE 8501

CMD ["python", "main.py"]
