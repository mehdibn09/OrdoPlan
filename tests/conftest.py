import pytest
from src.config import DATA
from src.schemas.pydantic_models import Instance
from src.storage.store import Store
from src.auth.auth_service import bootstrap


@pytest.fixture
def instance():
    return Instance.model_validate_json((DATA/"instances/demo.json").read_text())


@pytest.fixture
def store(tmp_path):
    value=Store(tmp_path/"test.sqlite3")
    bootstrap(value)
    return value


@pytest.fixture
def chef():
    return {"id":"chef","role":"chef","workshop":"ATELIER-1"}
