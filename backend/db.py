import os
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, ForeignKey, Text, JSON, Integer, Float, Boolean

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    sessions = relationship("AnalysisSession", back_populates="case", cascade="all, delete-orphan")

class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # uuid
    case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("cases.id"), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)  # Evidentiary integrity
    video_phash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frame_hashes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    input_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "file", "url", "text"
    status: Mapped[str] = mapped_column(String(50), default="pending")
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    case = relationship("Case", back_populates="sessions")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    details: Mapped[str] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

class TraceJob(Base):
    __tablename__ = "trace_jobs"
    
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    current_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None), onupdate=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class VideoFingerprint(Base):
    __tablename__ = "video_fingerprints"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=True)
    video_phash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audio_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    keyframe_hashes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    scene_hashes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class MediaOccurrence(Base):
    __tablename__ = "media_occurrences"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    fingerprint_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("video_fingerprints.id", ondelete="CASCADE"), nullable=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    mutation_type: Mapped[str] = mapped_column(String(100), default="Unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class PropagationEdge(Base):
    __tablename__ = "propagation_edges"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_occurrence: Mapped[int] = mapped_column(Integer, ForeignKey("media_occurrences.id", ondelete="CASCADE"), nullable=False)
    target_occurrence: Mapped[int] = mapped_column(Integer, ForeignKey("media_occurrences.id", ondelete="CASCADE"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

class MediaSearchCache(Base):
    __tablename__ = "media_search_cache"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    platform: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    ocr_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    video_phash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    keyframe_hashes: Mapped[list | None] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class EvidenceArtifact(Base):
    __tablename__ = "evidence_artifacts"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    collection_method: Mapped[str] = mapped_column(String(100), nullable=False)
    reliability: Mapped[float] = mapped_column(Float, default=1.0)
    value: Mapped[dict | list | str | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class SerpApiCache(Base):
    __tablename__ = "serpapi_cache"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    response_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    pipeline_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class LandmarkIntelligenceSession(Base):
    __tablename__ = "landmark_intelligence_sessions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    final_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_radius_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    final_city: Mapped[str | None] = mapped_column(String(200), nullable=True)
    final_region: Mapped[str | None] = mapped_column(String(200), nullable=True)
    final_country: Mapped[str | None] = mapped_column(String(200), nullable=True)
    overall_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    dominant_cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_frames_processed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frames_tier1_resolved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frames_tier2_resolved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class LandmarkDetection(Base):
    __tablename__ = "landmark_detections"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    frame_id: Mapped[str] = mapped_column(String(100), nullable=False)
    landmark_label: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_score: Mapped[float] = mapped_column(Float, nullable=False)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocoded: Mapped[bool] = mapped_column(Boolean, default=False)
    supporting_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class OCRDetection(Base):
    __tablename__ = "ocr_detections"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    frame_id: Mapped[str] = mapped_column(String(100), nullable=False)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False)
    ocr_source: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    resolved_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolved_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocoding_status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class L12ClusterResult(Base):
    __tablename__ = "l12_cluster_results"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.id", ondelete="CASCADE"), nullable=False)
    cluster_id: Mapped[int] = mapped_column(Integer, nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, nullable=False)
    weighted_member_count: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lng: Mapped[float] = mapped_column(Float, nullable=False)
    is_dominant: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

async def init_db():
    db_file = None
    if DATABASE_URL.startswith("sqlite+aiosqlite:///"):
        path_part = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        db_file = os.path.abspath(path_part)

    if db_file and os.path.exists(db_file):
        import sqlite3
        import shutil
        try:
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(analysis_sessions)")
            columns = [row[1] for row in cursor.fetchall()]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='serpapi_cache'")
            table_exists = cursor.fetchone()
            if table_exists:
                cursor.execute("PRAGMA table_info(serpapi_cache)")
                serp_cols = [row[1] for row in cursor.fetchall()]
                if "pipeline_version" not in serp_cols:
                    cursor.execute("ALTER TABLE serpapi_cache ADD COLUMN pipeline_version VARCHAR(50)")
                    cursor.execute("ALTER TABLE serpapi_cache ADD COLUMN prompt_version VARCHAR(50)")
                    conn.commit()
                    print("[DB] Added pipeline_version and prompt_version columns to serpapi_cache table.")
            conn.close()
            
            if columns and "video_phash" not in columns:
                backup_path = db_file + ".backup"
                shutil.copy2(db_file, backup_path)
                print(f"[DB] Schema mismatch detected. Old database backed up to {backup_path}")
                os.remove(db_file)
        except Exception as e:
            print(f"[DB] Schema compliance check failed: {e}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        try:
            from sqlalchemy import select, func
            result = await session.execute(select(func.count()).select_from(MediaSearchCache))
            count = result.scalar()
            if count == 0:
                print("[DB] Pre-seeding historical media search cache for demo targets...")
                sushi_phash = "f4c2e8e99b0d33e1"
                sushi_keyframes = ["f4c2e8e99b0d33e1", "12c2e8e99b0d3322", "88c2e8e99b0d3355"]
                
                seed1 = MediaSearchCache(
                    platform="Telegram",
                    url="https://t.me/kasamacura/status/49021893",
                    username="kasamacura",
                    caption="Original high-res footage from Tokyo metropolitan sushi kitchen.",
                    ocr_text="江戸前寿司 (Edomae Sushi) Chiyoda JR EAST Rail Terminal",
                    video_phash=sushi_phash,
                    keyframe_hashes=sushi_keyframes,
                    timestamp=datetime(2026, 6, 3, 12, 1, tzinfo=timezone.utc).replace(tzinfo=None),
                    first_seen=datetime(2026, 6, 3, 12, 1, tzinfo=timezone.utc).replace(tzinfo=None),
                    last_seen=datetime(2026, 6, 3, 12, 1, tzinfo=timezone.utc).replace(tzinfo=None)
                )
                seed2 = MediaSearchCache(
                    platform="X (Twitter)",
                    url="https://x.com/sushi_forensics/status/2046098263544357246",
                    username="sushi_forensics",
                    caption="Analyzing digital provenance on Tokyo kitchen rails. Check our site.",
                    ocr_text="江戸前寿司",
                    video_phash=sushi_phash,
                    keyframe_hashes=sushi_keyframes,
                    timestamp=datetime(2026, 6, 3, 12, 15, tzinfo=timezone.utc).replace(tzinfo=None),
                    first_seen=datetime(2026, 6, 3, 12, 15, tzinfo=timezone.utc).replace(tzinfo=None),
                    last_seen=datetime(2026, 6, 3, 12, 15, tzinfo=timezone.utc).replace(tzinfo=None)
                )
                seed3 = MediaSearchCache(
                    platform="Reddit",
                    url="https://reddit.com/r/sushiforensics/comments/t12345",
                    username="sushi_forensics",
                    caption="Check out this reposted video of Chiyoda rail sushi preparation.",
                    ocr_text="JR EAST",
                    video_phash=sushi_phash,
                    keyframe_hashes=sushi_keyframes,
                    timestamp=datetime(2026, 6, 3, 13, 30, tzinfo=timezone.utc).replace(tzinfo=None),
                    first_seen=datetime(2026, 6, 3, 13, 30, tzinfo=timezone.utc).replace(tzinfo=None),
                    last_seen=datetime(2026, 6, 3, 13, 30, tzinfo=timezone.utc).replace(tzinfo=None)
                )
                session.add_all([seed1, seed2, seed3])
                await session.commit()
                print("[DB] Seeding complete.")
        except Exception as seed_err:
            print(f"[DB] Seeding failed: {seed_err}")
            await session.rollback()

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
