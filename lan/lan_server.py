# lan_server.py
# LAN sunucusu - WebSocket üzerinden çok oyunculu oyunlar için

import asyncio
import json
from aiohttp import web, WSMsgType

HOST = "0.0.0.0"
PORT = 8080

# --- Hafıza durumu ---
clients = set()                # WebSocket bağlantıları
players = {}                   # player_id -> {"name": str, "score": int}
player_by_ws = {}              # ws -> player_id

def build_payload(type_, **data):
    out = {"type": type_}
    out.update(data)
    return json.dumps(out, ensure_ascii=False)

async def broadcast(msg: str):
    dead = []
    for ws in clients:
        try:
            await ws.send_str(msg)
        except:
            dead.append(ws)
    for ws in dead:
        await unregister(ws)

async def register(ws, player_name):
    import random
    pid = f"p{random.randint(100000, 999999)}"
    players[pid] = {"name": player_name[:24] or "Guest", "score": 0}
    player_by_ws[ws] = pid
    await send_state()
    return pid

async def unregister(ws):
    pid = player_by_ws.get(ws)
    if pid:
        players.pop(pid, None)
    player_by_ws.pop(ws, None)
    if ws in clients:
        clients.remove(ws)
    try:
        await send_state()
    except:
        pass

async def send_state():
    """Oyun durumunu yayınla - alt sınıflar tarafından override edilebilir"""
    state = {
        "players": [{"id": pid, "name": p["name"], "score": p["score"]} for pid, p in players.items()],
    }
    await broadcast(build_payload("state", **state))

async def handle_game_message(ws, data):
    """Oyun mesajlarını işle - alt sınıflar tarafından override edilmeli"""
    pass

# --- WebSocket Handler ---
async def ws_handler(request):
    ws = web.WebSocketResponse(heartbeat=20)
    await ws.prepare(request)
    clients.add(ws)
    await ws.send_str(build_payload("hello"))

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                except:
                    continue
                typ = data.get("type")

                if typ == "join":
                    name = (data.get("name") or "Guest").strip()
                    pid = await register(ws, name)
                    await ws.send_str(build_payload("joined", pid=pid, name=players[pid]["name"]))

                elif typ == "resume":
                    # tekrar bağlanma senaryosu
                    name = players.get(data.get("pid"), {"name":"Guest"})["name"]
                    pid = await register(ws, name)
                    await ws.send_str(build_payload("joined", pid=pid, name=name))

                else:
                    # Diğer mesajları oyun logiğine gönder
                    await handle_game_message(ws, data)

            elif msg.type == WSMsgType.ERROR:
                pass
            elif msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
                break
    except Exception as e:
        # Bağlantı hatalarını sessizce yönet
        pass
    finally:
        await unregister(ws)
        try:
            if not ws.closed:
                await ws.close()
        except:
            pass
    return ws

def create_app(index_html=None):
    """LAN server uygulaması oluştur"""
    app = web.Application()
    
    if index_html:
        async def index(request):
            return web.Response(text=index_html, content_type="text/html")
        app.router.add_get("/", index)
    
    app.router.add_get("/ws", ws_handler)
    return app

def run_server(app=None, port=PORT):
    """Sunucuyu başlat"""
    import socket
    import asyncio
    import sys
    
    if app is None:
        app = create_app()
    
    # Windows için asyncio policy ayarla
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print(f"🌐 Sunucu başlatıldı!")
    print(f"📍 Yerel erişim: http://localhost:{port}")
    print(f"🌍 LAN erişimi: http://{local_ip}:{port}")
    print(f"🔗 Diğer cihazlar bu adresi kullanabilir: http://{local_ip}:{port}")
    print(f"⚠️  Eğer bağlanamıyorsa Windows Güvenlik Duvarı'nı kontrol edin")
    print("-" * 50)
    
    web.run_app(app, host=HOST, port=port, print=None)

if __name__ == "__main__":
    print("⚠️  Bu dosya doğrudan çalıştırılamaz. Bir oyun dosyası kullanın.")
