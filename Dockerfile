FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y redis-tools

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENTRYPOINT ["python", "-u", "app.py"]
