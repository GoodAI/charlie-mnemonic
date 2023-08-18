FROM python:3.11 AS builder
# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements_local.txt

# Install nginx and supervisor
RUN apt-get update && apt-get install -y nginx supervisor

# Install gettext for envsubst command
RUN apt-get install -y gettext

# Remove default nginx configuration
RUN rm /etc/nginx/sites-enabled/default

# Copy nginx configuration
COPY nginx.local.conf.template /etc/nginx/sites-available/
COPY nginx.cloud.conf.template /etc/nginx/sites-available/

# Copy supervisor configuration
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 80 443 8001 8002

# Start supervisor
CMD if [ "$DEPLOY_ENV" = "local" ] ; then envsubst '\$PORT' < /etc/nginx/sites-available/nginx.local.conf.template > /etc/nginx/sites-enabled/nginx.local.conf && /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf ; else envsubst '\$PORT \$DOMAIN_NAME' < /etc/nginx/sites-available/nginx.cloud.conf.template > /etc/nginx/sites-enabled/nginx.cloud.conf && /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf ; fi