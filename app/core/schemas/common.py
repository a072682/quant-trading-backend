from typing import Any, Optional, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """標準 API 回應格式（單筆或無資料）"""
    success: bool = True
    message: str = "success"
    data: Optional[T] = None


class PaginationMeta(BaseModel):
    """分頁資訊"""
    total: int
    page: int
    limit: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """標準 API 回應格式（分頁列表）"""
    success: bool = True
    message: str = "success"
    data: list[T] = []
    pagination: Optional[PaginationMeta] = None
