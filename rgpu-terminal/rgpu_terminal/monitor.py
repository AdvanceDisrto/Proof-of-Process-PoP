"""Operator console: real Rich Live rendering of independently verified telemetry.
No screen-clearing loops. No synthetic producer enabled by merely watching.
"""
import asyncio
import httpx
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from .crypto import ReceiptError, ZERO_HASH, verify_envelope

async def monitor(url,pinned_pub):
    last=0;prev=ZERO_HASH
    async with httpx.AsyncClient(base_url=url,timeout=5) as client:
        with Live(refresh_per_second=3,screen=False) as live:
            while True:
                resp=await client.get('/api/history',params={'after':last,'limit':100})
                resp.raise_for_status()
                for envelope in resp.json()['envelopes']:
                    receipt=verify_envelope(envelope,pinned_pub,previous=prev,expected_sequence=last+1)
                    last=receipt['sequence'];prev=envelope['payload_sha256']
                    table=Table(show_header=False,expand=True)
                    for name,value in [('SEQUENCE',last),('SIGNED CLAIM',receipt['claim']),
                                       ('DECLARED VERDICT',receipt['declared_verdict']),
                                       ('SOURCE TIER',receipt['source_tier']),
                                       ('SHA256',prev),('PHYSICAL JOULES','NOT MEASURED'),
                                       ('SIGNATURE','VALID UNDER OPERATOR-PINNED SOFTWARE KEY'),
                                       ('PHYSICAL/CLINICAL TRUTH','NOT ESTABLISHED')]:
                        table.add_row(str(name),str(value))
                    live.update(Panel(table,title='i™ rGPU • VERIFIED DIGITAL TELEMETRY'))
                await asyncio.sleep(.5)
