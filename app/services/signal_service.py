from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.signal import Signal
from app.services.ai_service import ai_service

import httpx
from app.core.config import settings
from datetime import date


async def calculate_score(stock_code: str) -> dict:
    """
    計算指定股票的今日評分（法人 + 均線 + 成交量）
    回傳各參數得分與總分
    """
    institutional_score = 0
    ma_score = 0
    volume_score = 0

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            inst_response = await client.get(
                f"{settings.TWSE_BASE_URL}/MI_INDEX",
                params={"response": "json", "date": date.today().strftime("%Y%m%d")},
            )
            inst_data = inst_response.json()
            net_buy = inst_data.get("net_buy", 0)
            if net_buy > 1000:
                institutional_score = 2
            elif net_buy > 0:
                institutional_score = 1
            else:
                institutional_score = -2
    except Exception as e:
        print(f"  TWSE API 呼叫失敗，法人得分設為 0：{e}")
        institutional_score = 0

    # 均線得分（示意值，實際需呼叫富果行情 API 計算）
    ma_score = 1

    # 成交量得分（示意值，實際需呼叫富果行情 API 計算）
    volume_score = 1

    total_score = institutional_score + ma_score + volume_score

    return {
        "institutional_score": institutional_score,
        "ma_score": ma_score,
        "volume_score": volume_score,
        "total_score": total_score,
    }


async def create_today_signal(
    stock_code: str, stock_name: str, db: AsyncSession
) -> Signal:
    """
    計算今日評分 → 呼叫 AI 分析 → 儲存至資料庫
    若今日已有紀錄則更新，否則新增
    """
    today = date.today().strftime("%Y-%m-%d")
    scores = await calculate_score(stock_code)

    ai_result = await ai_service.analyze_signal({
        "stock_code": stock_code,
        "stock_name": stock_name,
        **scores,
    })

    result = await db.execute(
        select(Signal).where(
            Signal.stock_code == stock_code,
            Signal.date == today,
        )
    )
    signal = result.scalars().first()

    if signal:
        signal.institutional_score = scores["institutional_score"]
        signal.ma_score = scores["ma_score"]
        signal.volume_score = scores["volume_score"]
        signal.total_score = scores["total_score"]
        signal.ai_action = ai_result.get("action")
        signal.ai_reason = ai_result.get("reason")
    else:
        signal = Signal(
            date=today,
            stock_code=stock_code,
            stock_name=stock_name,
            institutional_score=scores["institutional_score"],
            ma_score=scores["ma_score"],
            volume_score=scores["volume_score"],
            total_score=scores["total_score"],
            ai_action=ai_result.get("action"),
            ai_reason=ai_result.get("reason"),
        )
        db.add(signal)

    await db.commit()
    await db.refresh(signal)

    return signal


async def get_today_signal(stock_code: str, db: AsyncSession) -> Signal:
    """從資料庫查詢指定股票的今日評分訊號"""
    today = date.today().strftime("%Y-%m-%d")
    result = await db.execute(
        select(Signal).where(
            Signal.stock_code == stock_code,
            Signal.date == today,
        )
    )
    return result.scalars().first()
