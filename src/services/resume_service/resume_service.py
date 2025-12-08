from src.llm_driver.llm_driver import LLMDriver
from src.llm_driver.agents.agents import LLMProvider, ModelNames
from src.llm_driver.schemas.response_schemas import SkillExtractionResponseSchema
from src.services.resume_service.resume_parser import ResumeParser
from src.database import db, DatabaseConnectionError
from typing import List
import os
import shutil

class ResumeUploadError(Exception):
    pass

class ResumeService:
    def __init__(self):
        self.llm_driver = LLMDriver(model_name=ModelNames.GPT_4_1, provider=LLMProvider.OPENAI, response_model=SkillExtractionResponseSchema, temperature=0.6)
        self.parser = ResumeParser()
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.allowed_extensions = {'.pdf'}

    def _validate_file(self, file_path: str):
        """Validate file before processing"""
        if not os.path.exists(file_path):
            raise ResumeUploadError("File not found")
        
        if not os.access(file_path, os.R_OK):
            raise ResumeUploadError("File is not readable")
        
        file_size = os.path.getsize(file_path)
        if file_size > self.max_file_size:
            raise ResumeUploadError(f"File too large ({file_size/1024/1024:.1f}MB). Max size: 10MB")
        
        if file_size == 0:
            raise ResumeUploadError("File is empty")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.allowed_extensions:
            raise ResumeUploadError("Only PDF files are supported")

    def upload_resume(self, user_id: int, file_path: str) -> int:
        temp_path = None
        try:
            # Validate file first
            self._validate_file(file_path)
            
            # Create uploads directory
            uploads_dir = "uploads"
            os.makedirs(uploads_dir, exist_ok=True)
            
            # Copy file with error handling
            file_name = os.path.basename(file_path)
            temp_path = os.path.join(uploads_dir, f"{user_id}_{file_name}")
            
            try:
                shutil.copy2(file_path, temp_path)
            except (OSError, IOError) as e:
                raise ResumeUploadError(f"Failed to copy file: {str(e)}")
            
            # Parse resume with error handling
            try:
                raw_text = self.parse_resume(temp_path)
                if not raw_text.strip():
                    raise ResumeUploadError("Resume appears to be empty or unreadable")
            except Exception as e:
                raise ResumeUploadError(f"Failed to parse resume: {str(e)}")
            
            # Database operations with transaction-like behavior
            try:
                result = db.execute_one(
                    "INSERT INTO Resumes (user_id, file_name, file_path, raw_text) VALUES (%s, %s, %s, %s) RETURNING resume_id",
                    (user_id, file_name, temp_path, raw_text)
                )
                
                if not result:
                    raise ResumeUploadError("Failed to save resume to database")
                
                resume_id = result['resume_id']
                
                # Extract and save skills
                try:
                    skills = self.extract_skills(raw_text)
                    self._save_skills(resume_id, skills)
                except Exception as e:
                    # Skills extraction failed, but resume is saved
                    print(f"Warning: Skill extraction failed: {str(e)}")
                
                return resume_id
                
            except DatabaseConnectionError:
                raise ResumeUploadError("Database connection lost during upload")
            except Exception as e:
                raise ResumeUploadError(f"Database error: {str(e)}")
                
        except Exception as e:
            # Cleanup on failure
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            raise

    def _save_skills(self, resume_id: int, skills: List[str]):
        """Save skills with error handling"""
        for skill_name in skills:
            try:
                skill_result = db.execute_one(
                    "INSERT INTO Skills (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name RETURNING skill_id",
                    (skill_name.lower(),)
                )
                
                if not skill_result:
                    skill_result = db.execute_one("SELECT skill_id FROM Skills WHERE name = %s", (skill_name.lower(),))
                
                if skill_result:
                    db.execute(
                        "INSERT INTO ResumeSkills (resume_id, skill_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (resume_id, skill_result['skill_id'])
                    )
            except Exception as e:
                print(f"Warning: Failed to save skill '{skill_name}': {str(e)}")

    def parse_resume(self, file_path: str) -> str:
        return self.parser._clean_text(self.parser._load_pdf(file_path))
    
    def extract_skills(self, resume_text: str) -> List[str]:
        return self.llm_driver.extract_skils(resume_text=resume_text)
    
    @staticmethod
    def get_user_resumes(user_id: int):
        return db.execute(
            "SELECT resume_id, file_name, uploaded_at FROM Resumes WHERE user_id = %s ORDER BY uploaded_at DESC",
            (user_id,)
        )


    @staticmethod
    def delete_resume(user_id: int, resume_id: int):
        # Verify ownership
        resume = db.execute_one(
            "SELECT file_path FROM Resumes WHERE resume_id = %s AND user_id = %s", 
            (resume_id, user_id)
        )
        if not resume:
            raise ResumeUploadError("Resume not found or access denied")

        db.execute("""
            DELETE FROM NGMIScores 
            WHERE application_id IN (
                SELECT application_id FROM Applications WHERE resume_id = %s
            )
        """, (resume_id,))
        db.execute("DELETE FROM Applications WHERE resume_id = %s", (resume_id,))
        db.execute("DELETE FROM ResumeSkills WHERE resume_id = %s", (resume_id,))
        db.execute("DELETE FROM Resumes WHERE resume_id = %s", (resume_id,))
        
        try:
            if os.path.exists(resume['file_path']):
                os.remove(resume['file_path'])
        except:
            pass  # File cleanup failed, but ignore

    @staticmethod
    def get_resume_details(resume_id: int):
        try:
            resume = db.execute_one("SELECT * FROM Resumes WHERE resume_id = %s", (resume_id,))
            
            if resume:
                skills = db.execute(
                    """SELECT s.name FROM Skills s 
                    JOIN ResumeSkills rs ON s.skill_id = rs.skill_id 
                    WHERE rs.resume_id = %s""",
                    (resume_id,)
                )
                resume['skills'] = [skill['name'] for skill in skills] if skills else []
            
            return resume
        except DatabaseConnectionError:
            raise ResumeUploadError("Database connection lost")
        except Exception as e:
            raise ResumeUploadError(f"Failed to retrieve resume: {str(e)}")
        
