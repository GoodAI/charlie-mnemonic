from starlette import status
from starlette.websockets import WebSocket


async def authenticate_websocket(websocket: WebSocket):
    session_token = websocket.cookies.get("session_token")
    username = websocket.cookies.get("username")
    if session_token:
        from authentication import Authentication

        auth = Authentication()
        if auth.check_token(username=username, session_token=session_token):
            await websocket.accept()
            await websocket.send_text("Connection successful")
            return True
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return False
