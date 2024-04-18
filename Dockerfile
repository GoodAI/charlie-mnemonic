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

# Dynamically add the Docker repository based on the detected architecture and release
RUN echo "deb [arch=$(dpkg --print-architecture)] https://download.docker.com/linux/debian $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list

# Install Docker CLI and ffmpeg, handle possible failure
RUN apt-get update && { apt-get install -y docker-ce-cli ffmpeg || true; }

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