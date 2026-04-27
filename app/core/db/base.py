from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有 ORM Model 的基底類別，所有 Model 必須繼承此類別"""
    pass
