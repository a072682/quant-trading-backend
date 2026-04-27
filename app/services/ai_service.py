# import json
# import re
# import anthropic

# from app.core.config import settings


# class AIService:
#     """Claude AI API 串接服務：負責分析評分數據並給出交易建議"""

#     def __init__(self):
#         self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

#     async def analyze_signal(self, signal_data: dict) -> dict:
#         prompt = f"""
# 你是一個台股量化交易分析師，請根據以下數據分析並給出建議。

# 股票資訊：
# - 代號：{signal_data['stock_code']}
# - 名稱：{signal_data['stock_name']}

# 評分數據：
# - 法人買賣超得分：{signal_data['institutional_score']}（+2=連續買超，+1=單日買超，-2=賣超）
# - 均線位置得分：{signal_data['ma_score']}（+2=在均線下方，+1=接近均線，-1=遠在均線上方）
# - 成交量得分：{signal_data['volume_score']}（+2=量放大1.5倍以上，0=正常，-1=量縮）
# - 總分：{signal_data['total_score']}（滿分5分，≥4建議買進）
# - 近期漲跌幅：{signal_data.get('recent_price_change', 0)}%

# 請根據以上數據：
# 1. 給出建議動作（buy / watch / sell 其中一個）
# 2. 用一句話說明原因（繁體中文，不超過50字）

# 請只回傳 JSON，不要加任何說明文字，格式如下：
# {{"action": "buy", "reason": "法人連續買超且股價位於均線下方，具備買進條件"}}
# """

#         try:
#             message = await self.client.messages.create(
#                 model="claude-sonnet-4-6",
#                 max_tokens=200,
#                 messages=[{"role": "user", "content": prompt}],
#             )

#             response_text = message.content[0].text.strip()

#             # 移除 markdown code block 包裝（```json ... ``` 或 ``` ... ```）
#             response_text = re.sub(r"^```(?:json)?\s*", "", response_text)
#             response_text = re.sub(r"\s*```$", "", response_text).strip()

#             result = json.loads(response_text)

#             if "action" not in result or "reason" not in result:
#                 raise ValueError("回應缺少必要欄位")

#         except Exception as e:
#             print(f"  AI 分析失敗：{e}")
#             result = {"action": "watch", "reason": "AI 分析暫時無法取得"}

#         return result


# ai_service = AIService()
