from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReviewCreate(StrictModel):
    card_id: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,160}$")
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ReviewCheck(StrictModel):
    item_id: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,160}$")
    checked: bool


class ReviewNote(StrictModel):
    text: str = Field(min_length=1, max_length=4000)


class ReviewDecision(StrictModel):
    status: str
    limitations: list[str] = Field(max_length=20)
    next_manual_step: str = Field(min_length=1, max_length=1000)


class TaskStart(StrictModel):
    confirmed: bool = False
