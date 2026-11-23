from pydantic import BaseModel, ConfigDict, Field, field_validator


class NameBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(..., min_length=1, max_length=100, description="Name, e.g. Python")

    @field_validator("name")
    @classmethod
    def collapse_spaces(cls, v: str) -> str:
        return " ".join(v.split())  # "Machine   Learning" -> "Machine Learning"


class SkillCreate(NameBase):
    pass


class SkillUpdate(NameBase):
    pass


class CategoryCreate(NameBase):
    pass


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class CategoryOut(BaseModel):
    id: int
    name: str
    skill_count: int = 0


class PopularSkillOut(BaseModel):
    id: int
    name: str
    candidates: int
    jobs: int
    total: int


class RelatedSkillOut(BaseModel):
    id: int
    name: str
    score: int


class DuplicateGroup(BaseModel):
    skills: list[SkillOut]


class MergeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: int
    duplicate_ids: list[int] = Field(..., min_length=1)


class MergeResult(BaseModel):
    merged_count: int
    target: SkillOut


class CandidateSkillCreate(NameBase):
    years_of_experience: int = Field(default=0, ge=0, le=60)


class CandidateSkillUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    years_of_experience: int = Field(..., ge=0, le=60)


class CandidateSkillOut(BaseModel):
    skill_id: int
    name: str
    years_of_experience: int


class JobSkillCreate(NameBase):
    is_required: bool = True


class JobSkillUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_required: bool


class JobSkillOut(BaseModel):
    skill_id: int
    name: str
    is_required: bool
