"""Astreum API — FastAPI server exposing node data over HTTP.

Endpoint modules live alongside this file: atom.py, list.py, chain.py,
block.py, accounts.py, transaction.py.  This module creates the app and
registers their routers.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from .deps import set_node as set_node     # re-exported for modes/headless.py
from .atom import router as atom_router
from .list import router as list_router
from .chain import router as chain_router
from .block import router as block_router
from .accounts import router as accounts_router
from .transaction import router as transaction_router

logger = logging.getLogger("astreum.api")

app = FastAPI(
    title="Astreum API",
    description="Read-only HTTP API for the Astreum blockchain platform.",
    version="0.1.0",
)


@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


app.include_router(atom_router)
app.include_router(list_router)
app.include_router(chain_router)
app.include_router(block_router)
app.include_router(accounts_router)
app.include_router(transaction_router)
