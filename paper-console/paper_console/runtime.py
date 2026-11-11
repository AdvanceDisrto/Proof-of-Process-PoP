"""Bounded async print scheduling built atop a durable SQLite outbox.

No fake events generated. No printer enabled unless an operator constructs a sink.
"""
from __future__ import annotations
import asyncio
from .escpos import PrintScheduler


class AsyncPrinterWorker:
    def __init__(self, scheduler: PrintScheduler, *, poll_seconds: float = 1.0,
                 max_notifications: int = 128):
        if not 0.2 <= poll_seconds <= 60:
            raise ValueError("invalid poll interval")
        self.scheduler = scheduler
        self._queue=asyncio.Queue(maxsize=max_notifications)
        self.poll_seconds = poll_seconds
        self.running=False
        self.completed=0
        self.last_result=None

    def notify(self):
        """Best-effort wakeup only; durable outbox persists across shutdown."""
        try:self._queue.put_nowait(1)
        except asyncio.QueueFull:pass

    async def run(self):
        self.running=True
        try:
            while self.running:
                # Sinks are blocking I/O and must never stall the event loop.
                self.last_result=await asyncio.to_thread(self.scheduler.process_once)
                if self.last_result.get('status')=='SENT_UNCONFIRMED':
                    self.completed+=1
                try:await asyncio.wait_for(self._queue.get(),timeout=self.poll_seconds)
                except asyncio.TimeoutError:pass
        finally:self.running=False

    def stop(self):
        self.running=False
        self.notify()
