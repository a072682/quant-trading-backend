from fastapi import APIRouter

from app.api.v1.endpoints import auth, positions, signals, simulation, stocks, trades

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["Auth"])
router.include_router(signals.router, prefix="/signals", tags=["Signals"])
router.include_router(stocks.router, prefix="/stocks", tags=["Stocks"])
router.include_router(trades.router, prefix="/trades", tags=["Trades"])
router.include_router(positions.router, prefix="/positions", tags=["Positions"])
router.include_router(simulation.router, prefix="/simulation", tags=["Simulation"])
