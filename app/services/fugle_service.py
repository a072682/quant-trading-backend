# import httpx

# from app.core.config import settings


# class FugleService:
#     """富果 API 串接服務：負責行情查詢與下單執行"""

#     def __init__(self):
#         self.base_url = "https://api.fugle.tw/marketdata/v1.0"
#         self.headers = {
#             "X-API-KEY": settings.FUGLE_API_KEY,
#         }

#     async def get_stock_price(self, stock_code: str) -> float:
#         """查詢指定股票的目前成交價格"""
#         async with httpx.AsyncClient() as client:
#             response = await client.get(
#                 f"{self.base_url}/stock/intraday/quote/{stock_code}",
#                 headers=self.headers,
#             )
#             data = response.json()
#             return data.get("closePrice", 0.0)

#     async def place_buy_order(
#         self, stock_code: str, shares: int, price: float
#     ) -> dict:
#         """送出買進委託單給富果 API"""
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{self.base_url}/order",
#                 headers=self.headers,
#                 json={
#                     "stockNo": stock_code,
#                     "buySell": "B",
#                     "quantity": shares,
#                     "price": price,
#                     "apCode": "1",
#                 },
#             )
#             return response.json()

#     async def place_sell_order(
#         self, stock_code: str, shares: int, price: float
#     ) -> dict:
#         """送出賣出委託單給富果 API"""
#         async with httpx.AsyncClient() as client:
#             response = await client.post(
#                 f"{self.base_url}/order",
#                 headers=self.headers,
#                 json={
#                     "stockNo": stock_code,
#                     "buySell": "S",
#                     "quantity": shares,
#                     "price": price,
#                     "apCode": "1",
#                 },
#             )
#             return response.json()

#     async def get_positions(self) -> list:
#         """查詢目前帳戶持倉（庫存股票）"""
#         async with httpx.AsyncClient() as client:
#             response = await client.get(
#                 f"{self.base_url}/account/inventories",
#                 headers=self.headers,
#             )
#             return response.json().get("data", [])


# fugle_service = FugleService()
