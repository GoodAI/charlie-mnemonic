FROM python:3.10
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV HOST=0.0.0.0
ENV PORT=8002

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY .env_docker /app/.env
COPY . /app
EXPOSE 8002
# Install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Cleanup to reduce image size.
RUN apt-get clean && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["python", "launcher.py"]