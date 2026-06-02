"""
WebSocket routes — real-time price feed.

Client connects to:
    ws://localhost:8000/api/v1/ws/prices?symbols=XAUUSD,DXY,VIX

Then receives push messages whenever fetch_all_ticks fires:
    {"type": "tick", "symbol": "XAUUSD", "data": {"price": 2050.12, "bid": ..., ...}}

Client can also send:
    {"action": "subscribe",   "symbols": ["NDX"]}
    {"action": "unsubscribe", "symbols": ["NDX"]}
"""

import json
from typing import Optional

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.logger import get_logger
from app.services.websocket.manager import ws_manager

logger = get_logger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])

_DEFAULT_SYMBOLS = ["XAUUSD", "DXY", "VIX", "SPX"]


@router.websocket("/prices")
async def prices_feed(
    websocket: WebSocket,
    symbols: Optional[str] = Query(
        default=None,
        description="Comma-separated list of symbols, e.g. XAUUSD,DXY,VIX",
    ),
):
    """
    Real-time price feed via WebSocket.
    Broadcasts tick updates as soon as the Celery poller fetches them.
    """
    requested = (
        [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if symbols
        else _DEFAULT_SYMBOLS
    )

    await ws_manager.connect(websocket, symbols=requested)
    logger.info(f"WS /prices connected — {requested}")

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
                action = msg.get("action", "")
                syms = [s.upper() for s in msg.get("symbols", [])]

                if action == "subscribe" and syms:
                    for s in syms:
                        ws_manager._subscriptions.setdefault(s, set()).add(websocket)
                    await websocket.send_json({"type": "ack", "subscribed": syms})

                elif action == "unsubscribe" and syms:
                    for s in syms:
                        ws_manager._subscriptions.get(s, set()).discard(websocket)
                    await websocket.send_json({"type": "ack", "unsubscribed": syms})

                elif action == "ping":
                    await websocket.send_json({"type": "pong"})

            except (json.JSONDecodeError, KeyError):
                pass  # ignore malformed client messages

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WS /prices disconnected")


@router.websocket("/status")
async def status_feed(websocket: WebSocket):
    """Lightweight status channel — broadcasts system-wide messages."""
    await ws_manager.connect(websocket, symbols=[])
    try:
        while True:
            await websocket.receive_text()   # keep alive
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
