#region 引入套件
# DeclarativeBase：SQLAlchemy 提供的基底類別
# 繼承它才能讓 SQLAlchemy 認識並管理這個類別
from sqlalchemy.orm import DeclarativeBase
#endregion




#region 基底類別：Base — 所有資料表設計圖的共同祖先
# 作用：作為所有資料表設計圖的集合點
# 所有資料表設計圖（User、Signal 等）都必須繼承這個類別
#
# 為什麼需要它：
# main.py 啟動時執行 Base.metadata.create_all
# SQLAlchemy 會自動找到所有繼承 Base 的類別
# 並在資料庫建立對應的資料表
#
# 輸入：無（只是定義一個空的基底類別）
# 輸出：一個讓所有資料表設計圖繼承的共同起點
class Base(DeclarativeBase):

    # pass 代表這個類別沒有自己的內容
    # 完全繼承 DeclarativeBase 的功能
    # 不需要加任何東西，空的才是正確的
    pass
#endregion
