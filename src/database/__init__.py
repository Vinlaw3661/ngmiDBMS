import os
from dotenv import load_dotenv
import psycopg
from psycopg.rows import dict_row

load_dotenv()


class Database:
    def __init__(self):
        self.conn = None
        self.connect()

    def connect(self):
        try:
            self.conn = psycopg.connect(
                host=os.getenv("DB_HOST", "localhost"),
                dbname=os.getenv("DB_NAME", "ngmidbms"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "password"),
                port=os.getenv("DB_PORT", "5432"),
                row_factory=dict_row,
                autocommit=True,
            )
        except Exception as e:
            print(f"Database connection failed: {e}")
            raise

    def execute(self, query, params=None):
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchall()
            return None

    def execute_one(self, query, params=None):
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:
                return cur.fetchone()
            return None

    def setup_tables(self):
        queries = [
            """CREATE TABLE IF NOT EXISTS Users (
                user_id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS Resumes (
                resume_id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                raw_text TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES Users(user_id)
            )""",
            """CREATE TABLE IF NOT EXISTS Skills (
                skill_id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS ResumeSkills (
                resume_id INTEGER NOT NULL,
                skill_id INTEGER NOT NULL,
                PRIMARY KEY(resume_id, skill_id),
                FOREIGN KEY(resume_id) REFERENCES Resumes(resume_id),
                FOREIGN KEY(skill_id) REFERENCES Skills(skill_id)
            )""",
            """CREATE TABLE IF NOT EXISTS JobPostings (
                job_id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                description TEXT NOT NULL
            )""",
            """CREATE TABLE IF NOT EXISTS Applications (
                application_id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                job_id INTEGER NOT NULL,
                resume_id INTEGER NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'submitted',
                UNIQUE(user_id, job_id),
                FOREIGN KEY(user_id) REFERENCES Users(user_id),
                FOREIGN KEY(job_id) REFERENCES JobPostings(job_id),
                FOREIGN KEY(resume_id) REFERENCES Resumes(resume_id)
            )""",
            """CREATE TABLE IF NOT EXISTS NGMIScores (
                ngmi_id SERIAL PRIMARY KEY,
                application_id INTEGER NOT NULL,
                ngmi_score REAL NOT NULL,
                ngmi_comment TEXT NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(application_id) REFERENCES Applications(application_id)
            )""",
        ]

        for query in queries:
            self.execute(query)

        sample_jobs = [
            (
                "Software Engineer",
                "TechCorp",
                "Looking for a Python developer with 3+ years experience. Must know Django, PostgreSQL, and have strong problem-solving skills.",
            ),
            (
                "Data Scientist",
                "DataFlow Inc",
                "Seeking ML engineer with Python, TensorFlow, and statistics background. PhD preferred but not required.",
            ),
            (
                "Frontend Developer",
                "WebWorks",
                "React/TypeScript developer needed. Must have experience with modern CSS, REST APIs, and agile development.",
            ),
            (
                "DevOps Engineer",
                "CloudFirst",
                "AWS/Docker expert wanted. Kubernetes, CI/CD, and infrastructure as code experience required.",
            ),
            (
                "Product Manager",
                "StartupXYZ",
                "Technical PM with engineering background. Must understand software development lifecycle and user research.",
            ),
        ]

        for title, company, desc in sample_jobs:
            existing = self.execute_one(
                "SELECT job_id FROM JobPostings WHERE title = %s AND company = %s",
                (title, company),
            )
            if not existing:
                self.execute(
                    "INSERT INTO JobPostings (title, company, description) VALUES (%s, %s, %s)",
                    (title, company, desc),
                )


db = Database()
