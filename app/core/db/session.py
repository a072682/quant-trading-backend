#region 引入 SQLAlchemy 非同步套件
from sqlalchemy.ext.asyncio import (
    # create_async_engine：建立非同步資料庫引擎（連線的核心）
    create_async_engine,
    # async_sessionmaker：建立非同步連線池的工廠函式
    async_sessionmaker,
    # AsyncSession：每一次資料庫操作所使用的連線物件
    AsyncSession,
)
#endregion

#region 引入設定檔
# db_config：提供組合好的 DATABASE_URL 連線字串
from app.core.config.database_config import db_config
# app_config：提供 APP_ENV 判斷控制文件頁面是否開放、哪些前端可以呼叫後端
from app.core.config.app_config import app_config
#endregion

#region 建立資料庫引擎
# 引擎是程式和資料庫之間的「溝通橋樑」
# 知道去哪裡連、怎麼連（連線規則）
# 輸入：DATABASE_URL 連線字串
# 輸出：engine（可以跟資料庫溝通的物件）
engine = create_async_engine(
    # 使用 database_config 組合好的連線字串
    db_config.DATABASE_URL,

    # 開發環境下，把每一行 SQL 指令印出來方便除錯
    # 輸入：APP_ENV = "development" → 輸出：True（開啟）
    # 輸入：APP_ENV = "production"  → 輸出：False（關閉）
    # echo是sqlalchemy專門的變數 只要為True就會印出所有 SQL 操作
    echo=app_config.APP_ENV == "development",

    # 每次借用連線前，先確認連線是否還活著
    # 避免拿到已經斷掉的舊連線
    pool_pre_ping=True,

    # 連線超過 300 秒（5分鐘）自動回收
    # 避免 Neon 雲端資料庫閒置太久自動斷線
    pool_recycle=300,

    # 連線池最多同時保持 5 條連線待命
    # 由於非同步特性可以多請求同步運行
    # 一個請求會占用一個通道
    # 常駐狀態會有五條通道常駐開啟
    pool_size=5,

    # 5 條不夠用時，最多可以額外借 10 條
    # 也就是最多同時 15 條連線
    max_overflow=10,

    # asyncpg 連接 Neon 的必要設定
    # 停用 prepared statement 快取
    # 避免連線重建後舊快取失效造成錯誤
    connect_args={"statement_cache_size": 0},
)
#endregion

#region 建立連線池工廠
# AsyncSessionLocal 是一個「工廠」
# 每次需要查詢時，負責借出和歸還連線
# 輸入：engine（引擎）
# 輸出：AsyncSessionLocal（可以產生連線的工廠）
AsyncSessionLocal = async_sessionmaker(
    # 綁定上面建立好的引擎
    bind=engine,

    # 指定每次借出的連線物件類型為 AsyncSession
    class_=AsyncSession,

    # commit 之後不自動把物件變成「過期」狀態
    # 避免 commit 後還要重新查詢才能使用資料
    expire_on_commit=False,
)
#endregion
