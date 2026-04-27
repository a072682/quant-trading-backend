from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db
from app.core.models.user_model import User
from app.core.security import verify_password, create_access_token, hash_password
from app.schemas.common import APIResponse

from pydantic import BaseModel

router = APIRouter()


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterIn(BaseModel):
    email: str
    username: str
    password: str


@router.post("/login", response_model=APIResponse[TokenOut])
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """登入並取得 JWT Token"""
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="帳號或密碼錯誤",
        )

    token = create_access_token(subject=user.id)
    return APIResponse(
        message="登入成功",
        data=TokenOut(access_token=token),
    )


@router.post("/register", response_model=APIResponse[TokenOut], status_code=201)
async def register(
    data: RegisterIn,
    db: AsyncSession = Depends(get_db),
):
    """註冊新使用者"""
    existing = await db.execute(
        select(User).where(User.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="此 Email 已被註冊",
        )

    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(subject=user.id)
    return APIResponse(
        message="註冊成功",
        data=TokenOut(access_token=token),
    )
