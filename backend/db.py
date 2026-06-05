import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Integer

# Place database in backend workspace directory
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "helix.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class Case(Base):
    __tablename__ = "cases"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    sessions = relationship("AnalysisSession", back_populates="case", cascade="all, delete-orphan")

class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cases.id"), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    input_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "file", "url", "text"
    status: Mapped[str] = mapped_column(String(50), default="pending")
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    case = relationship("Case", back_populates="sessions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    details: Mapped[str] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
