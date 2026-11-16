"""Contrats métier. Toutes les dates sont des minutes depuis 08:00, journée fictive."""
from typing import Literal
from importlib.metadata import version
from pydantic import BaseModel, Field, model_validator


class Source(BaseModel):
    document_id: str
    page: int = Field(ge=1)
    element_id: str
    version: str = "1.0"


class Order(BaseModel):
    id: str = Field(pattern=r"^OF-\d{3,6}$")
    reference: str
    family: str
    quantity: int = Field(gt=0, le=10000)
    unit_minutes: int = Field(gt=0, le=600)
    due: int = Field(gt=0, le=10080)
    release: int = Field(default=0, ge=0)
    priority: int = Field(default=1, ge=1, le=10)
    eligible: list[str] = Field(min_length=1)
    tool: str | None = None
    operator: str | None = None
    note: str = Field(default="", max_length=2000)
    sources: dict[str, Source]

    @property
    def duration(self):
        return self.quantity * self.unit_minutes


class Window(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)

    @model_validator(mode="after")
    def valid(self):
        if self.end <= self.start:
            raise ValueError("Fin d'indisponibilité antérieure au début")
        return self


class Machine(BaseModel):
    id: str
    initial_family: str = "ALU"
    unavailable: list[Window] = Field(default_factory=list)
    source: Source


class Operation(BaseModel):
    order_id: str
    machine: str
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    setup: int = Field(ge=0)


class Instance(BaseModel):
    id: str
    workshop_id: str = "ATELIER-1"
    orders: list[Order] = Field(min_length=1, max_length=30)
    machines: list[Machine] = Field(min_length=1, max_length=8)
    setup: dict[str, int]
    setup_source: Source
    horizon: int = Field(default=720, gt=0, le=10080)
    now: int = Field(default=0, ge=0)
    resource_unavailable: dict[str, list[Window]] = Field(default_factory=dict)
    frozen: list[Operation] = Field(default_factory=list)
    baseline: list[Operation] = Field(default_factory=list)

    @model_validator(mode="after")
    def consistency(self):
        ids = [o.id for o in self.orders]
        mids = [m.id for m in self.machines]
        if len(ids) != len(set(ids)) or len(mids) != len(set(mids)):
            raise ValueError("Identifiants dupliqués")
        for o in self.orders:
            if not set(o.eligible) <= set(mids):
                raise ValueError("Machine inconnue")
            for field in ("duration", "eligible", "tool", "release", "due"):
                if field not in o.sources:
                    raise ValueError(f"Source obligatoire : {o.id}.{field}")
        frozen_ids = [f.order_id for f in self.frozen]
        if len(frozen_ids) != len(set(frozen_ids)) or not set(frozen_ids) <= set(ids):
            raise ValueError("Gel invalide")
        if self.now > self.horizon:
            raise ValueError("Instant courant hors horizon")
        return self

    def changeover(self, before, after):
        if before == after:
            return 0
        key = f"{before}>{after}"
        if key not in self.setup:
            raise ValueError(f"Temps de réglage non sourcé : {key}")
        return self.setup[key]


class Schedule(BaseModel):
    status: Literal["OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "MODEL_INVALID"]
    operations: list[Operation] = Field(default_factory=list)
    weighted_tardiness: int = 0
    makespan: int = 0
    stability: int = 0
    primary_bound: float | None = None
    elapsed_seconds: float = 0
    violations: list[str] = Field(default_factory=list)
    solver_version: str = "ortools-"+version("ortools")
    instance_id: str


class Citation(Source):
    excerpt: str


class Answer(BaseModel):
    status: Literal["answered", "needs_clarification", "refused", "proposed", "infeasible"]
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tool_results: list[dict] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    proposed_action: dict | None = None
    schedule: Schedule | None = None
    diff: dict | None = None
    trace: list[str] = Field(default_factory=list)
    versions: dict = Field(default_factory=dict)
