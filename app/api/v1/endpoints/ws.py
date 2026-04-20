from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

import asyncio
import json
import random

router = APIRouter()

connected_clients: list[WebSocket] = []

WATCH_LIST = ["0050", "0056", "2886", "2412", "5880"]

# 富果 API 尚未串接，先用模擬基準價產生隨機波動
_MOCK_BASE_PRICES = {
    "0050": 185.0,
    "0056": 35.0,
    "2886": 42.5,
    "2412": 128.0,
    "5880": 22.5,
}


def _get_mock_price(stock_code: str) -> float:
    base = _MOCK_BASE_PRICES.get(stock_code, 100.0)
    return round(base + random.uniform(-0.5, 0.5), 2)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端點：前端連線後開始接收即時股價推送
    連線路徑：ws://localhost:8000/ws
    """
    await websocket.accept()
    connected_clients.append(websocket)

    try:
        while True:
            if websocket.application_state != WebSocketState.CONNECTED:
                break

            for stock in WATCH_LIST:
                if websocket.application_state != WebSocketState.CONNECTED:
                    break
                try:
                    price = _get_mock_price(stock)
                    await websocket.send_text(json.dumps({
                        "code": stock,
                        "price": price,
                    }))
                except Exception:
                    # 傳送失敗代表連線已斷，跳出內層迴圈讓外層檢查狀態
                    break

            await asyncio.sleep(10)

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print("WebSocket 客戶端已斷線")
