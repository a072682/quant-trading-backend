from fastapi import APIRouter

from app.api.v1.endpoints import auth, signals, trades, positions

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(signals.router, prefix="/signals", tags=["Signals"])
router.include_router(trades.router, prefix="/trades", tags=["Trades"])
router.include_router(positions.router, prefix="/positions", tags=["Positions"])
