from src.database import db
from src.services.ngmi_service import generate_ngmi
from src.database import db, DatabaseConnectionError
from src.services.job_service.job_parser import JobParser, JobParseError

class JobApplicationError(Exception):
    pass

job_parser = JobParser()

def add_job_from_url(url: str) -> int:
    try:
        job_details = job_parser.extract_from_url(url)
        
        # Check if job already exists
        existing = db.execute_one(
            "SELECT job_id FROM JobPostings WHERE title = %s AND company = %s",
            (job_details.title, job_details.company)
        )
        
        if existing:
            raise ValueError(f"Job '{job_details.title}' at {job_details.company} already exists")
        
        result = db.execute_one(
            "INSERT INTO JobPostings (title, company, description) VALUES (%s, %s, %s) RETURNING job_id",
            (job_details.title, job_details.company, job_details.description)
        )
        
        return result['job_id']
        
    except JobParseError:
        raise
    except Exception as e:
        raise JobParseError(f"Database error: {str(e)}")

def delete_job(job_id: int):
    # Check if job has applications
    apps = db.execute_one("SELECT COUNT(*) as count FROM Applications WHERE job_id = %s", (job_id,))
    if apps['count'] > 0:
        raise ValueError("Cannot delete job with existing applications")
    
    result = db.execute("DELETE FROM JobPostings WHERE job_id = %s", (job_id,))
    if not result:
        raise ValueError("Job not found")


def apply_to_job(user_id: int, job_id: int, resume_id: int) -> int:
    try:
        # Check for existing application
        existing = db.execute_one(
            "SELECT application_id FROM Applications WHERE user_id = %s AND job_id = %s",
            (user_id, job_id)
        )
        if existing:
            # Return the existing application to surface its current NGMI score/comment
            return existing["application_id"]
        
        # Validate resume belongs to user
        resume = db.execute_one(
            "SELECT raw_text FROM Resumes WHERE resume_id = %s AND user_id = %s", 
            (resume_id, user_id)
        )
        if not resume:
            raise JobApplicationError("Resume not found or doesn't belong to you")
        
        # Validate job exists
        job = db.execute_one("SELECT description FROM JobPostings WHERE job_id = %s", (job_id,))
        if not job:
            raise JobApplicationError("Job posting not found")
        
        # Create application
        app_result = db.execute_one(
            "INSERT INTO Applications (user_id, job_id, resume_id) VALUES (%s, %s, %s) RETURNING application_id",
            (user_id, job_id, resume_id)
        )
        
        if not app_result:
            raise JobApplicationError("Failed to create application")
        
        application_id = app_result['application_id']
        
        # Generate NGMI score with error handling
        try:
            ngmi_response = generate_ngmi(resume['raw_text'], job['description'])

            ngmi_score, ngmi_comment, ngmi_feedback = ngmi_response.not_gonna_make_it_score, ngmi_response.justification, ngmi_response.feedback

            db.execute(
                "INSERT INTO NGMIScores (application_id, ngmi_score, ngmi_comment, feedback) VALUES (%s, %s, %s, %s)",
                (application_id, ngmi_score, ngmi_comment, ngmi_feedback)
            )
        except Exception as e:
            # Application created but NGMI failed - still return success
            print(f"Warning: NGMI generation failed: {str(e)}")
        
        return application_id
        
    except DatabaseConnectionError:
        raise JobApplicationError("Database connection lost during application")
    except JobApplicationError:
        raise
    except Exception as e:
        raise JobApplicationError(f"Application failed: {str(e)}")


def list_jobs() -> list:
    return db.execute("SELECT * FROM JobPostings ORDER BY job_id")

def get_job_details(job_id: int):
    return db.execute_one("SELECT * FROM JobPostings WHERE job_id = %s", (job_id,))

def get_user_applications(user_id: int):
    return db.execute(
        """SELECT a.application_id, a.applied_at, a.status,
                  j.title, j.company,
                  n.ngmi_score, n.ngmi_comment
           FROM Applications a
           JOIN JobPostings j ON a.job_id = j.job_id
           LEFT JOIN NGMIScores n ON a.application_id = n.application_id
           WHERE a.user_id = %s
           ORDER BY a.applied_at DESC""",
        (user_id,)
    )

def get_ngmi_history(application_id: int):
    return db.execute_one(
        """SELECT a.application_id, j.title, j.company, j.description,
                  r.file_name, n.ngmi_score, n.ngmi_comment, n.generated_at
           FROM Applications a
           JOIN JobPostings j ON a.job_id = j.job_id
           JOIN Resumes r ON a.resume_id = r.resume_id
           JOIN NGMIScores n ON a.application_id = n.application_id
           WHERE a.application_id = %s""",
        (application_id,)
    )

def delete_application(user_id: int, application_id: int):
    # Verify ownership
    app = db.execute_one(
        "SELECT application_id FROM Applications WHERE application_id = %s AND user_id = %s",
        (application_id, user_id)
    )
    if not app:
        raise JobApplicationError("Application not found or access denied")
    
    # Delete application (cascades to NGMIScores)
    db.execute("DELETE FROM Applications WHERE application_id = %s", (application_id,))
