from fastapi import FastAPI, Query, Form, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import shutil
import os
import tempfile
from . import db

# Import services
from src.services import auth_service
from src.services.job_service import job_service
from src.services.resume_service.resume_service import ResumeService
from src.database import db as src_db

app = FastAPI(title="ngmiDBMS API")

@app.on_event("startup")
async def startup_event():
    try:
        src_db.setup_tables()
    except Exception as e:
        print(f"Database setup failed: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/register")
def register(email: str = Form(...), password: str = Form(...), full_name: str = Form(...)):
    try:
        user_id = auth_service.register_user(email, full_name, password)
        # Auto login after register
        user = auth_service.login_user(email, password)
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/login")
def login(email: str = Form(...), password: str = Form(...)):
    try:
        user = auth_service.login_user(email, password)
        return user
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs")
def get_jobs():
    return db.fetch_all("SELECT * FROM JobPostings ORDER BY job_id DESC")


@app.post("/api/upload_resume")
def upload_resume(user_id: int = Form(...), file: UploadFile = File(...)):
    try:
        # Create a temp directory and save the file with its original name there
        temp_dir = tempfile.mkdtemp()
        temp_file_path = os.path.join(temp_dir, file.filename)
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        service = ResumeService()
        resume_id = service.upload_resume(user_id, temp_file_path)
        
        # Cleanup
        shutil.rmtree(temp_dir)
        
        return {"resume_id": resume_id, "file_name": file.filename}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/apply")
def apply(user_id: int = Form(...), job_id: int = Form(...), resume_id: int = Form(...)):
    try:
        app_id = job_service.apply_to_job(user_id, job_id, resume_id)
        
        score_data = src_db.execute_one(
            "SELECT ngmi_score, ngmi_comment FROM NGMIScores WHERE application_id = %s",
            (app_id,)
        )
        
        return {
            "application_id": app_id,
            "ngmi_score": score_data['ngmi_score'] if score_data else None,
            "ngmi_comment": score_data['ngmi_comment'] if score_data else None
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/users/{user_id}/applications")
def get_applications(user_id: int):
    """
    Return all applications for a user, including any NGMI scores already generated.
    """
    try:
        return job_service.get_user_applications(user_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/applications/{application_id}/ngmi")
def get_application_ngmi(application_id: int):
    """
    Return NGMI details for a specific application.
    """
    try:
        details = job_service.get_ngmi_history(application_id)
        if not details:
            raise HTTPException(status_code=404, detail="Application not found or no NGMI score yet")
        return details
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/schema")
def api_schema():
    tables, columns, fks = db.fetch_schema()
    return {"tables": tables, "columns": columns, "fks": fks}


@app.get("/api/counts")
def api_counts():
    tables, _, _ = db.fetch_schema()
    counts = db.fetch_table_counts(tables) if tables else []
    return counts


@app.get("/api/preview")
def api_preview(table: str = Query(...), limit: Optional[int] = Query(None)):
    if not table:
        return {"columns": [], "rows": []}
    limit_val = int(limit) if limit else db.ROW_LIMIT
    df = db.fetch_table_preview(table, limit_val)
    cols = list(df.columns) if not df.empty else []
    rows = df.to_dict("records") if not df.empty else []
    return {"columns": cols, "rows": rows}


@app.get("/api/activity")
def api_activity(limit: Optional[int] = Query(20)):
    limit_val = int(limit) if limit else 20
    act = db.fetch_activity(limit_val)
    return act
