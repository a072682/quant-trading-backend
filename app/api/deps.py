# TODO: 此檔案已拆分
# get_db           → app/core/db/session.py
# get_current_user → app/core/auth/security.py

# from fastapi import Depends, HTTPException, status
# from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.db.session import AsyncSessionLocal
# from app.core.security import decode_token

# bearer_scheme = HTTPBearer()


# async def get_db():
#     """依賴注入：提供資料庫 Session，請求結束後自動關閉"""
#     async with AsyncSessionLocal() as session:
#         yield session


# async def get_current_user(
#     credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
#     db: AsyncSession = Depends(get_db),
# ):
#     """依賴注入：驗證 JWT Token，回傳目前登入的使用者"""
#     user_id = decode_token(credentials.credentials)

#     if not user_id:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Token 無效或已過期",
#         )

#     return user_id
