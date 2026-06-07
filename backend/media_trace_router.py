import os
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db, TraceJob, AnalysisSession, AuditLog
import logging
logger = logging.getLogger("helix.trace_router")

async def verify_api_key(x_api_key: str = Header(default=None)):
    expected_key = os.getenv("API_KEY", "")
    if expected_key and x_api_key != expected_key:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Key")


router = APIRouter()

# Global in-memory dictionary to hold running background tasks so they can be cancelled
_active_tasks = {}

class URLTraceRequest(BaseModel):
    url: str
    case_id: Optional[int] = None

class TraceJobResponse(BaseModel):
    job_id: str
    session_id: str
    status: str
    progress: int
    current_stage: str

@router.post("/analysis-sessions/{session_id}/global-trace", response_model=TraceJobResponse, dependencies=[Depends(verify_api_key)])
async def trigger_global_trace(session_id: str, db: AsyncSession = Depends(get_db)):
    """Starts global media dissemination tracking for an existing analysis session."""
    from backend import request_id_var
    from media_trace_service import run_trace_pipeline
    # Verify session exists
    result = await db.execute(select(AnalysisSession).where(AnalysisSession.id == session_id))
    session_record = result.scalar_one_or_none()
    if not session_record:
        raise HTTPException(status_code=404, detail="Analysis session not found.")

    if session_record.status != "completed":
        raise HTTPException(status_code=400, detail="Cannot trace a session that is not fully analyzed.")

    job_id = str(uuid.uuid4())
    
    # Create persistent job in trace_jobs table
    db_job = TraceJob(
        id=job_id,
        session_id=session_id,
        status="pending",
        progress=0,
        current_stage="Preparing Fingerprints"
    )
    db.add(db_job)
    
    # Audit log
    audit = AuditLog(
        action="global_media_trace",
        details=f"Trace job {job_id} initiated for session {session_id}.",
        request_id=request_id_var.get()
    )
    db.add(audit)
    await db.commit()

    # Schedule background trace execution
    task = asyncio.create_task(run_trace_pipeline(job_id, session_id))
    _active_tasks[job_id] = task
    
    return {
        "job_id": job_id,
        "session_id": session_id,
        "status": "pending",
        "progress": 0,
        "current_stage": "Preparing Fingerprints"
    }


async def download_and_trace_task(job_id: str, session_id: str, url_target: str, case_id: Optional[int]) -> None:
    """Background task to download a media URL, analyze it, and run the dissemination trace."""
    try:
        from backend import get_async_client, is_safe_url, save_file_to_uploads, process_file_bytes
        from media_trace_service import update_job_stage
        await update_job_stage(job_id, "Preparing Fingerprints", 5)
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 OSINT-Forensics"
        }
        
        # Stream download file bytes (SSRF protected)
        client = get_async_client()
        content = b""
        async with client.stream("GET", url_target, headers=headers, timeout=15, follow_redirects=True) as response:
            if not is_safe_url(str(response.url)):
                raise Exception("Target URL redirects to an unsafe network destination.")
            if response.status_code != 200:
                raise Exception(f"HTTP network error code: {response.status_code}")
            
            async for chunk in response.aiter_bytes(chunk_size=8192):
                content += chunk
                if len(content) > 100 * 1024 * 1024:
                    raise Exception("Downloaded media size exceeds 100MB limit.")

        if not content:
            raise Exception("Downloaded media file is empty.")

        filename = url_target.split("/")[-1].split("?")[0] or "url_traced_media.mp4"
        if not any(filename.lower().endswith(ext) for ext in [".mp4", ".png", ".jpg", ".jpeg", ".webp"]):
            filename = f"{filename}.mp4"

        # Create session in db
        saved_filename = save_file_to_uploads(session_id, filename, content)
        file_hash = hashlib.md5(content).hexdigest()

        async with db_write_lock_router():
            async with async_session() as db_session:
                new_session = AnalysisSession(
                    id=session_id,
                    case_id=case_id,
                    filename=filename,
                    file_hash=file_hash,
                    input_type="url",
                    status="pending"
                )
                db_session.add(new_session)
                await db_session.commit()

        # Run primary forensic analysis
        await update_job_stage(job_id, "Preparing Fingerprints", 10)
        async with async_session() as db_session:
            results = await process_file_bytes(
                content, filename, origin_url=url_target, session_id=session_id, saved_filename=saved_filename, db=db_session
            )
            
            # Update session status
            res_session = await db_session.execute(select(AnalysisSession).where(AnalysisSession.id == session_id))
            sess_rec = res_session.scalar_one_or_none()
            if sess_rec:
                sess_rec.status = "completed"
                sess_rec.results = results
                sess_rec.sha256 = results.get("sha256")
                
                lower_name = filename.lower()
                is_video_ext = any(lower_name.endswith(ext) for ext in [".mp4", ".webm", ".avi", ".mov", ".mkv"])
                sess_rec.video_phash = results.get("phash") if is_video_ext else None
                sess_rec.frame_hashes = results.get("frame_hashes", [])
                
                if results.get("video_analysis"):
                    vid = results["video_analysis"]
                    sess_rec.frame_count = vid.get("frame_count", 0)
                    sess_rec.duration = vid.get("duration", 0.0)
                    sess_rec.fps = vid.get("fps", 0.0)
                
                db_session.add(sess_rec)
                await db_session.commit()

        # Continue with trace pipeline
        from media_trace_service import run_trace_pipeline
        await run_trace_pipeline(job_id, session_id, origin_url=url_target)

    except Exception as e:
        logger.exception(f"URL Trace task failed: {e}")
        from media_trace_service import update_job_stage
        await update_job_stage(job_id, "Completed", 100, f"URL Ingestion Error: {str(e)}")


def db_write_lock_router():
    from media_trace_service import _db_write_lock
    return _db_write_lock


import asyncio

@router.post("/global-trace/url", response_model=TraceJobResponse, dependencies=[Depends(verify_api_key)])
async def trigger_url_trace(payload: URLTraceRequest, db: AsyncSession = Depends(get_db)):
    """Downloads a media URL and launches a global trace job concurrently."""
    from backend import is_safe_url, request_id_var
    if not is_safe_url(payload.url):
        raise HTTPException(status_code=400, detail="URL is invalid or points to an unsafe destination.")

    session_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    # Create trace job
    db_job = TraceJob(
        id=job_id,
        session_id=session_id,
        status="pending",
        progress=0,
        current_stage="Preparing Fingerprints"
    )
    db.add(db_job)
    
    # Audit log
    audit = AuditLog(
        action="global_media_trace",
        details=f"Trace job {job_id} initiated for URL: {payload.url}",
        request_id=request_id_var.get()
    )
    db.add(audit)
    await db.commit()

    # Schedule download & trace background task
    task = asyncio.create_task(download_and_trace_task(job_id, session_id, payload.url, payload.case_id))
    _active_tasks[job_id] = task

    return {
        "job_id": job_id,
        "session_id": session_id,
        "status": "pending",
        "progress": 0,
        "current_stage": "Preparing Fingerprints"
    }


@router.get("/global-trace/jobs/{job_id}", dependencies=[Depends(verify_api_key)])
async def get_trace_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieves trace job progress, current stage, and results when completed."""
    result = await db.execute(select(TraceJob).where(TraceJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Trace job not found.")

    res_data = {
        "job_id": job.id,
        "session_id": job.session_id,
        "status": job.status,
        "progress": job.progress,
        "current_stage": job.current_stage,
        "error_message": job.error_message,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "results": job.result_json
    }
    return res_data


@router.post("/global-trace/jobs/{job_id}/cancel", dependencies=[Depends(verify_api_key)])
async def cancel_trace_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Cancels a running trace job."""
    result = await db.execute(select(TraceJob).where(TraceJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Trace job not found.")

    if job.status not in ("pending", "running"):
         raise HTTPException(status_code=400, detail="Cannot cancel a job that has already finished.")

    # Cancel active background task
    if job_id in _active_tasks:
        task = _active_tasks[job_id]
        task.cancel()
        del _active_tasks[job_id]
        logger.info(f"Cancelled running trace job task: {job_id}")

    job.status = "failed"
    job.current_stage = "Cancelled"
    job.error_message = "Job cancelled by investigator."
    db.add(job)
    
    # Audit log
    from backend import request_id_var
    audit = AuditLog(
        action="global_media_trace",
        details=f"Trace job {job_id} was manually cancelled.",
        request_id=request_id_var.get()
    )
    db.add(audit)
    await db.commit()

    return {"message": f"Job {job_id} cancelled successfully."}
