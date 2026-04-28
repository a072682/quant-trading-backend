#region 引入套件
# Any：代表任意類型（目前未使用，保留備用）
# Optional：代表「有值或是 None」
# Generic：讓類別可以接受泛型參數（T）
# TypeVar：定義泛型佔位符號
from typing import Any, Optional, Generic, TypeVar

# BaseModel：pydantic 提供的資料格式基底類別
# 繼承它的類別會自動驗證欄位類型，並支援轉換成 JSON
from pydantic import BaseModel
#endregion


#region 定義泛型佔位符號
# T 是一個佔位符號，代表「使用時再決定是什麼類型」
# 讓 APIResponse 可以適用於不同 API 的回傳資料
# 輸入範例：APIResponse[TokenOut] → T 換成 TokenOut
# 輸入範例：APIResponse[None]     → T 換成 None（無資料）
T = TypeVar("T")
#endregion


#region 標準回傳格式：APIResponse — 單筆或無資料
# 作用：所有 API 統一使用這個格式回傳給前端
# 輸入範例：APIResponse[TokenOut](message="登入成功", data=TokenOut(...))
# 輸出範例：
# {
#   "success": true,
#   "message": "登入成功",
#   "data": {"access_token": "eyJxxx", "token_type": "bearer"}
# }
class APIResponse(BaseModel, Generic[T]):
    # 是否成功，預設為 True
    success: bool = True
    # 說明訊息，預設為 "success"
    message: str = "success"
    # 回傳的資料，類型由 T 決定，預設為 None（無資料）
    data: Optional[T] = None
#endregion


#region 分頁資訊格式：PaginationMeta
# 作用：當 API 回傳大量資料時，附上分頁相關資訊
# 輸入範例：PaginationMeta(total=100, page=1, limit=10, total_pages=10)
# 輸出範例：
# {
#   "total": 100,        ← 總筆數
#   "page": 1,           ← 目前第幾頁
#   "limit": 10,         ← 每頁幾筆
#   "total_pages": 10    ← 總共幾頁
# }
class PaginationMeta(BaseModel):
    # 總筆數
    total: int
    # 目前第幾頁
    page: int
    # 每頁幾筆
    limit: int
    # 總共幾頁
    total_pages: int
#endregion


#region 標準回傳格式：PaginatedResponse — 分頁列表
# 作用：回傳大量資料時使用，附上分頁資訊
# 輸入範例：PaginatedResponse[SignalOut](message="取得成功", data=[...], pagination=PaginationMeta(...))
# 輸出範例：
# {
#   "success": true,
#   "message": "取得成功",
#   "data": [...],
#   "pagination": {"total": 100, "page": 1, "limit": 10, "total_pages": 10}
# }
class PaginatedResponse(BaseModel, Generic[T]):
    # 是否成功，預設為 True
    success: bool = True
    # 說明訊息，預設為 "success"
    message: str = "success"
    # 回傳的資料列表，預設為空列表
    data: list[T] = []
    # 分頁資訊，若無分頁則為 None
    pagination: Optional[PaginationMeta] = None
#endregion
