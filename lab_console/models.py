from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ReviewCreate(StrictModel):
    case_id: str = Field(default="legacy_case", pattern=r"^[a-z0-9_]{3,100}$")
    card_id: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,160}$")
    source_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_bundle_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_semantic_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class ReviewCheck(StrictModel):
    item_id: str = Field(pattern=r"^[A-Za-z0-9_.:-]{1,160}$")
    checked: bool


class ReviewProgress(StrictModel):
    current_step: str
    completed_step_ids: list[str] = Field(max_length=9)
    unresolved_item_ids: list[str] = Field(max_length=500)


class ReviewItemState(StrictModel):
    state: str


class ReviewNote(StrictModel):
    text: str = Field(min_length=1, max_length=4000)


class ReviewDecision(StrictModel):
    status: str
    limitations: list[str] = Field(max_length=20)
    next_manual_step: str = Field(min_length=1, max_length=1000)
    operator_summary: str = Field(default="Рассмотрение выполнено в пределах лабораторных данных.", min_length=1, max_length=4000)


class ReviewComplete(StrictModel):
    operator_summary: str = Field(min_length=1, max_length=4000)
    next_manual_step: str = Field(min_length=1, max_length=1000)
    limitations: list[str] = Field(max_length=20)


class TaskStart(StrictModel):
    confirmed: bool = False


class LaboratoryRunCreate(StrictModel):
    template_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    candidate_token: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    input_token: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")
    run_kind: str = Field(pattern=r"^[a-z][a-z0-9_]{2,79}$")
    environment_profile: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")


class LaboratoryRunExecute(StrictModel):
    confirmed: bool
    recovery_boundary: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9_-]{1,79}$")


class LaboratoryRunRecovery(StrictModel):
    action: str = Field(pattern=r"^(continue|mark_failed)$")


class RunComparisonCreate(StrictModel):
    left_run_token: str = Field(pattern=r"^run-[a-f0-9]{20}$")
    right_run_token: str = Field(pattern=r"^run-[a-f0-9]{20}$")


class ComparisonReviewPatch(StrictModel):
    status: str | None = None
    completed_steps: list[str] | None = Field(default=None, max_length=13)
    reviewed_dimensions: list[str] | None = Field(default=None, max_length=20)
    unresolved_differences: list[str] | None = Field(default=None, max_length=100)
    recommended_manual_action: str | None = None
    operator_summary: str | None = Field(default=None, max_length=4000)
    limitations: list[str] | None = Field(default=None, max_length=30)


class ComparisonReviewNote(StrictModel):
    text: str = Field(min_length=1, max_length=4000)
