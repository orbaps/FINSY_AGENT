FROM python:3.10-slim

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/app/db /app/app/models

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app/finsy_service.py"]
