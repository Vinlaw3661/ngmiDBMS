from pydantic import BaseModel, Field

class NotGonnaMakeItScoreResponseSchema(BaseModel):
    not_gonna_make_it_score: float = Field(...,description="A score between 0 and 1 indicating the likelihood of not making it")
    justification: str = Field(...,description="A brief justification for the score provided")
    feedback: str = Field(..., description="A brief feedback for the score provided")

class SkillExtractionResponseSchema(BaseModel):
    skills: list[str] = Field(..., description="A list of skills extracted from the resume text")
