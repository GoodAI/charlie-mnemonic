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
ENTRYPOINT ["python", "launcher.py"]