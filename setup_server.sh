#!/bin/bash

# Update and install Nginx and Certbot
sudo apt update
sudo apt install -y nginx software-properties-common
sudo add-apt-repository universe
sudo add-apt-repository ppa:certbot/certbot
sudo apt update
sudo apt install -y certbot python3-certbot-nginx

# Remove any existing symbolic link
sudo rm -f /etc/nginx/sites-enabled/*

# Create Nginx configuration without SSL
echo "server {
    listen 80;
    server_name chat.airobin.net;
    location / {
        proxy_pass http://localhost:8002;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}" | sudo tee /etc/nginx/sites-available/chat.airobin.net

# Obtain SSL certificate
sudo certbot --nginx -d chat.airobin.net

# Create Nginx configuration with SSL
echo "server {
    listen 80;
    server_name chat.airobin.net;
    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 443 ssl;
    server_name chat.airobin.net;

    ssl_certificate /etc/letsencrypt/live/chat.airobin.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/chat.airobin.net/privkey.pem;

    location / {
        proxy_pass http://localhost:8002;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}" | sudo tee /etc/nginx/sites-available/chat.airobin.net

# Enable the site
sudo ln -sf /etc/nginx/sites-available/chat.airobin.net /etc/nginx/sites-enabled/

# Test Nginx configuration and restart
sudo nginx -t
sudo systemctl restart nginx

# Start Docker
docker run --env-file .env -e DEPLOY_ENV=cloud -e ORIGINS="chat.airobin.net" -e PORT=8002 -p 8002:8002 -v G:\GoodAI\CLANG\userdata\:/app/users alloin/clang:v1