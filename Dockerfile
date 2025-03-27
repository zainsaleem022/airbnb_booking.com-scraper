# Use a slim Python image based on Debian
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for Playwright/Chromium
RUN apt-get update && apt-get install -y \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only)
RUN python -m playwright install chromium

# Copy all Python files
COPY main.py .
COPY booking.py .
COPY airbnb.py .

# Set environment variable to ensure Playwright finds Chromium
ENV PLAYWRIGHT_BROWSERS_PATH=/root/.cache/ms-playwright

# Command to run your main script
CMD ["python", "main.py"]
