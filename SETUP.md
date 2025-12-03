# ngmiDBMS Setup Instructions

## Prerequisites

1. **PostgreSQL**: Install and start PostgreSQL server
2. **Python 3.12+**: Ensure Python is installed
3. **OpenAI API Key**: Get from https://platform.openai.com/api-keys

## Setup Steps

### 1. Database Setup
```bash
# Create PostgreSQL database
createdb ngmidbms

# Or using psql:
psql -c "CREATE DATABASE ngmidbms;"
```

### 2. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings:
# - Database credentials
# - OpenAI API key
```

### 3. Install Dependencies
```bash
# Install project dependencies
pip install -e .
```

### 4. Run Application
```bash
python main.py

```

## Usage Examples

### Basic Workflow
```
> register
Email: john@example.com
Full name: John Doe
Password: ********
User registered successfully (ID: 1)

> login
Email: john@example.com
Password: ********
Welcome back, John Doe!

(john@example.com) > upload_resume
Resume file path: /path/to/resume.pdf
Extracting text...
Detected skills: python, sql, javascript, react
Resume uploaded (ID = 1)

(john@example.com) > list_jobs
Available Jobs:
ID: 1 | Software Engineer at TechCorp
ID: 2 | Data Scientist at DataFlow Inc
...

(john@example.com) > apply
Job ID: 1
Resume ID: 1
Generating NGMI evaluation...
Match score: 67.3
NGMI Score: 42.1
NGMI Comment: "Your Python skills are decent but your resume screams 'I learned React last week'. Mid energy."
Application submitted.
```

## File Structure
```
ngmiDBMS/
├── main.py              # Entry point
├── src/
│   ├── database.py      # Database connection & schema
│   ├── models.py        # Data models
│   ├── auth_service.py  # User authentication
│   ├── resume_service.py # Resume management
│   ├── job_service.py   # Job applications
│   ├── matching_service.py # Resume-job matching
│   ├── ngmi_service.py  # NGMI score generation
│   ├── llm_utils.py     # LLM utilities
│   └── cli.py           # CLI interface
├── uploads/             # Resume file storage
└── .env                 # Environment configuration
```

## Troubleshooting

- **Database connection failed**: Check PostgreSQL is running and credentials in `.env`
- **LLM errors**: Verify OpenAI API key is set correctly
- **File upload errors**: Ensure file paths are correct and files exist
