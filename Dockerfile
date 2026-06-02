FROM python:3.12-slim

WORKDIR /app

# DejaVu fonts are used as fallback when no custom TTF is present in assets/fonts/
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Output directory is created at runtime; mount a volume to persist images
RUN mkdir -p output

CMD ["python", "main.py"]
