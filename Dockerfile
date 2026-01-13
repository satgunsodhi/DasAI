FROM python:3.11-slim

WORKDIR /app

# Force unbuffered Python output for logs
ENV PYTHONUNBUFFERED=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY bot.py .

# Run the bot (don't copy .env - use Railway env vars)
CMD ["python", "bot.py"]
