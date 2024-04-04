FROM python:3.10

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV HOST=0.0.0.0
ENV PORT=8002

# Update and install dependencies
RUN apt-get update && \
    apt-get install -y apt-transport-https \
                       ca-certificates \
                       curl \
                       gnupg \
                       lsb-release 

# Add Docker GPG key
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/trusted.gpg.d/docker.gpg

# Add Docker's official APT repository
RUN echo "deb [arch=amd64] https://download.docker.com/linux/debian buster stable" > /etc/apt/sources.list.d/docker.list

# Install Docker CLI and ffmpeg
RUN apt-get update && \
    apt-get install -y docker-ce-cli \
                       ffmpeg

WORKDIR /app
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --upgrade --quiet duckduckgo-search
COPY .env_docker /app/.env
COPY . /app
EXPOSE 8002

# Cleanup to reduce image size.
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["python", "launcher.py"]
