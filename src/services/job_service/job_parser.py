import requests
from bs4 import BeautifulSoup
from src.llm_driver.llm_driver import LLMDriver
from src.llm_driver.agents.agents import LLMProvider, ModelNames
from pydantic import BaseModel

class JobDetails(BaseModel):
    title: str
    company: str
    description: str

class JobParseError(Exception):
    pass

class JobParser:
    def __init__(self):
        self.llm_driver = LLMDriver(
            model_name=ModelNames.GPT_4_1, 
            provider=LLMProvider.OPENAI, 
            response_model=JobDetails,
            temperature=0.1
        )
        self.max_chars = 8000

    def extract_from_url(self, url: str) -> JobDetails:
        try:

            headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
            
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                element.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            
            if len(text) > self.max_chars:
                text = text[:self.max_chars] + "..."
            
            if not text.strip():
                raise JobParseError("No readable content found")
    
            return self.llm_driver.extract_job_details(job_description=text)
            
        except requests.RequestException as e:
            raise JobParseError(f"Failed to fetch URL: {str(e)}")
        except Exception as e:
            raise JobParseError(f"Parsing failed: {str(e)}")
