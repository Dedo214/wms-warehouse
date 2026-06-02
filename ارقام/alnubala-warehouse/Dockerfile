FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV FLASK_ENV=production
ENV PORT=7860
EXPOSE 7860
CMD gunicorn --bind 0.0.0.0:$PORT --worker-class eventlet --workers 1 --timeout 120 wsgi:application
