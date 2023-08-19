# Start Docker
# Online
docker run --env-file .env -e DEPLOY_ENV=cloud -e ORIGINS="chat.airobin.net" -e PORT=8002 -p 8002:8002 -v G:\GoodAI\CLANG\userdata\:/app/users alloin/clang:v1

# Offline
docker run --env-file .env -e DEPLOY_ENV=local -e PORT=8002 -p 8002:8002 -v G:\GoodAI\CLANG\userdata\:/app/users alloin/clang:v1