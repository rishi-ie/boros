"""
Agent Message Bus — in-memory pub/sub for agent communication.
Messages flow through the bus; handlers subscribe to message types.
"""

from __future__ import annotations
import threading
import queue
from typing import Callable
from agents.messages import AgentMessage, MessageType


class AgentBus:
    """
    In-memory message bus for agent communication.
    Subscribers register handlers for specific message types.
    """

    def __init__(self):
        self._handlers: dict[MessageType, list[Callable[[AgentMessage], None]]] = {}
        self._queue: queue.Queue[AgentMessage] = queue.Queue()
        self._running = False
        self._thread: threading.Thread | None = None

    def subscribe(
        self, msg_type: MessageType, handler: Callable[[AgentMessage], None]
    ) -> None:
        """Subscribe to a message type."""
        if msg_type not in self._handlers:
            self._handlers[msg_type] = []
        self._handlers[msg_type].append(handler)

    def unsubscribe(
        self, msg_type: MessageType, handler: Callable[[AgentMessage], None]
    ) -> None:
        """Unsubscribe a handler."""
        if msg_type in self._handlers:
            try:
                self._handlers[msg_type].remove(handler)
            except ValueError:
                pass

    def publish(self, message: AgentMessage) -> None:
        """Publish a message to all subscribers."""
        self._queue.put(message)

    def send(self, message: AgentMessage) -> None:
        """Alias for publish."""
        self.publish(message)

    def start(self) -> None:
        """Start the message processing loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the message processing loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def _process_loop(self) -> None:
        """Process messages from the queue."""
        while self._running:
            try:
                msg = self._queue.get(timeout=0.5)
                for handler in self._handlers.get(msg.type, []):
                    try:
                        handler(msg)
                    except Exception as e:
                        print(f"[AgentBus] Handler error: {e}")
            except queue.Empty:
                continue

    def clear(self) -> None:
        """Clear all handlers."""
        self._handlers.clear()

    def stats(self) -> dict:
        """Get bus statistics."""
        return {
            "handlers": {mt.value: len(hs) for mt, hs in self._handlers.items()},
            "queue_size": self._queue.qsize(),
            "running": self._running,
        }


# Global bus instance
_bus: AgentBus | None = None


def get_bus() -> AgentBus:
    global _bus
    if _bus is None:
        _bus = AgentBus()
    return _bus


def reset_bus() -> None:
    """Reset the global bus (useful for testing)."""
    global _bus
    if _bus:
        _bus.stop()
    _bus = None