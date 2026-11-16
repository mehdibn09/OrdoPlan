import yaml
from src.config import ROOT


def load_prompt(name):
    allowed={"extract_work_order_v1","read_machine_display_v1","explain_schedule_v1","evidence_check_v1","publication_draft_v1"}
    if name not in allowed:
        raise ValueError("Prompt non versionné")
    return yaml.safe_load((ROOT/"prompts"/(name+".yaml")).read_text(encoding="utf-8"))
