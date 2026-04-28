#region 引入套件
# json：解析 Claude 回傳的 JSON 格式結果
import json

# anthropic：Anthropic 官方 SDK，用於呼叫 Claude AI 模型
import anthropic

# api_config：讀取 ANTHROPIC_API_KEY 環境變數
from app.core.config.api_config import api_config
#endregion


#region 常數設定
# 使用的 Claude 模型版本
CLAUDE_MODEL = "claude-sonnet-4-6"

# AI 分析結果的最大 token 數（JSON 格式，300 個 token 已足夠）
MAX_TOKENS = 300
#endregion


#region 函式：analyze_signal — 將評分資料送給 Claude AI 分析，回傳買進建議
# 作用：將量化評分整理成提示詞，送給 Claude AI 判斷今日是否值得買入
# 輸入：
#   stock_code（股票代號，字串，例如 "2330"）
#   stock_name（股票名稱，字串，例如 "台積電"）
#   scores（評分字典，包含所有分項分數與總分）
# 輸出：字典
#   {"ai_action": "buy/watch/sell", "ai_reason": "說明", "confidence": 0-100}
# 容錯處理：AI 分析失敗時回傳 watch + confidence=0，不中斷主流程
async def analyze_signal(
    stock_code: str,
    stock_name: str,
    scores: dict,
) -> dict:
    """將評分資料送給 Claude AI 分析，回傳 ai_action、ai_reason、confidence"""

    print(f"[AI分析] 開始分析 {stock_code} {stock_name}...")

    try:
        # 建立 Anthropic 非同步客戶端
        # 使用 AsyncAnthropic 避免阻塞 asyncio 事件迴圈
        client = anthropic.AsyncAnthropic(api_key=api_config.ANTHROPIC_API_KEY)

        # 組合提示詞，將量化評分轉化為 AI 可理解的格式
        prompt = f"""你是一個台股分析師，請根據以下量化評分資料判斷這支股票今日是否值得買入。

股票代號：{stock_code}
股票名稱：{stock_name}

今日評分明細：
  法人買賣超得分：{scores.get("institutional_score", 0)}（範圍 -2 到 +2，正值代表法人買超）
  均線位置得分：{scores.get("ma_score", 0)}（範圍 -1 到 +2，正值代表股價在均線附近或以下）
  成交量得分：{scores.get("volume_score", 0)}（範圍 -1 到 +2，正值代表成交量放大）
  殖利率得分：{scores.get("yield_score", 0)}（範圍 -1 到 +2，正值代表殖利率高）
  大盤情緒得分：{scores.get("futures_score", 0)}（範圍 -2 到 +2，正值代表大盤偏多）
  總分：{scores.get("total_score", 0)}

請回傳 JSON 格式，不要有任何其他文字：
{{
  "ai_action": "buy 或 watch 或 sell 其中一個",
  "ai_reason": "50 字以內的繁體中文說明",
  "confidence": 0 到 100 的整數（代表對買入決策的信心程度，越高越值得買入）
}}"""

        # 呼叫 Claude AI 模型進行分析
        response = await client.messages.create(
            # 指定使用的模型版本
            model=CLAUDE_MODEL,
            # 限制回傳的最大 token 數
            max_tokens=MAX_TOKENS,
            messages=[
                # user 角色：將提示詞送給 Claude
                {"role": "user", "content": prompt}
            ],
        )

        # 取出回應文字（Claude 回傳的 JSON 字串）
        raw_text = response.content[0].text.strip()

        # 解析 JSON 格式的回應
        result = json.loads(raw_text)

        # 確認必要欄位都存在，若缺少則填入預設值
        ai_action = result.get("ai_action", "watch")
        ai_reason = result.get("ai_reason", "AI 分析結果不完整")
        confidence = int(result.get("confidence", 0))

        print(f"[AI分析] {stock_code} 結果：{ai_action}，信心：{confidence}")

        # 回傳格式：{"ai_action": ..., "ai_reason": ..., "confidence": ...}
        return {
            "ai_action": ai_action,
            "ai_reason": ai_reason,
            "confidence": confidence,
        }

    except Exception as e:
        # AI 分析失敗時，記錄錯誤但不中斷主流程
        # 回傳 watch（觀望）作為保守預設值
        print(f"[AI分析] {stock_code} 分析失敗：{e}")
        return {
            # watch：無法判斷時保守觀望
            "ai_action": "watch",
            # 說明 AI 服務暫時無法使用
            "ai_reason": "AI 分析服務暫時無法使用",
            # 信心值為 0，代表無參考價值
            "confidence": 0,
        }
#endregion
