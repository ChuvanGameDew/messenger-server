from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

# Разрешаем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

clients = {}  # {user_id: websocket}


@app.get("/")
def home():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok", "clients": len(clients)}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    user_id = None

    try:
        while True:
            data = await websocket.receive_text()

            try:
                msg_data = json.loads(data)

                # Аутентификация
                if msg_data.get("type") == "auth":
                    user_id = msg_data["user_id"]
                    clients[user_id] = websocket
                    print(f"✅ User {user_id} connected. Total: {len(clients)}")
                    continue

                # Пересылка сообщения
                if msg_data.get("type") == "message":
                    receiver_id = msg_data["receiver_id"]
                    if receiver_id in clients:
                        try:
                            await clients[receiver_id].send_text(json.dumps(msg_data))
                            print(f"📨 Message sent to {receiver_id}")
                        except:
                            print(f"Failed to send to {receiver_id}")

                # Обновление списка друзей
                if msg_data.get("type") == "update_friends":
                    user_id_to_update = msg_data.get("target_user_id")
                    if user_id_to_update in clients:
                        await clients[user_id_to_update].send_text(json.dumps({
                            "type": "refresh_friends"
                        }))
                        print(f"🔄 Friends list refresh sent to {user_id_to_update}")

                # Обновление списка заявок
                if msg_data.get("type") == "refresh_requests":
                    user_id_to_update = msg_data.get("target_user_id")
                    if user_id_to_update in clients:
                        await clients[user_id_to_update].send_text(json.dumps({
                            "type": "refresh_requests"
                        }))
                        print(f"🔄 Requests list refresh sent to {user_id_to_update}")

                # Новая заявка в друзья
                if msg_data.get("type") == "new_friend_request":
                    user_id_to_update = msg_data.get("target_user_id")
                    if user_id_to_update in clients:
                        await clients[user_id_to_update].send_text(json.dumps({
                            "type": "new_friend_request"
                        }))
                        print(f"📨 Friend request notification sent to {user_id_to_update}")

                # Друг удалил чат
                if msg_data.get("type") == "friend_deleted":
                    friend_id = msg_data.get("friend_id")
                    if friend_id in clients:
                        await clients[friend_id].send_text(json.dumps({
                            "type": "friend_deleted",
                            "friend_id": user_id
                        }))
                        print(f"🗑 Friend deleted notification sent to {friend_id}")

            except json.JSONDecodeError:
                print(f"Invalid JSON: {data}")

    except WebSocketDisconnect:
        if user_id and user_id in clients:
            del clients[user_id]
        print(f"❌ User {user_id} disconnected. Total: {len(clients)}")


if __name__ == "__main__":
    import uvicorn
    # Для локального запуска
    uvicorn.run(app, host="0.0.0.0", port=8000)
