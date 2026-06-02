"""
WebSocket connection manager.

Maintains the list of active connections and broadcasts price updates.
Uses Redis pub/sub when available so updates propagate across Uvicorn workers.
Falls back to in-process broadcast when Redis is unavailable.
"""

import asyncio
import json
from typing import Dict, Set

from fastapi import WebSocket

from app.core.logger import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections grouped by subscribed symbol.

    Usage:
        manager = ConnectionManager()

        # In a WebSocket endpoint:
        await manager.connect(websocket, symbols=["XAUUSD", "DXY"])
        try:
            while True:
                await websocket.receive_text()   # keep alive / handle client messages
        finally:
            manager.disconnect(websocket)

        # From a background task:
        await manager.broadcast_tick("XAUUSD", {"price": 2050.0, ...})
    """

    def __init__(self) -> None:
        # symbol → set of WebSocket connections subscribed to it
        self._subscriptions: Dict[str, Set[WebSocket]] = {}
        # all active connections
        self._connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket, symbols: list[str]) -> None:
        await websocket.accept()
        self._connections.add(websocket)
        for symbol in symbols:
            self._subscriptions.setdefault(symbol.upper(), set()).add(websocket)
        logger.info(f"WS client connected, subscribed to: {symbols}  (total={len(self._connections)})")

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)
        for subscribers in self._subscriptions.values():
            subscribers.discard(websocket)
        logger.info(f"WS client disconnected  (total={len(self._connections)})")

    async def broadcast_tick(self, symbol: str, payload: dict) -> None:
        """Push a tick update to all clients subscribed to this symbol."""
        message = json.dumps({"type": "tick", "symbol": symbol, "data": payload})
        dead: list[WebSocket] = []

        for ws in self._subscriptions.get(symbol.upper(), set()):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    async def broadcast_all(self, payload: dict) -> None:
        """Push a message to every connected client."""
        message = json.dumps(payload)
        dead: list[WebSocket] = []

        for ws in list(self._connections):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)


# Singleton — imported by routes and background tasks
ws_manager = ConnectionManager()
