"""Régression : planning, brouillon MES et citation identique dans deux onglets."""
from streamlit.testing.v1 import AppTest
from src.config import ROOT
from src.solver.cp_sat import solve


def test_all_tabs_can_render_same_schedule_and_source(monkeypatch,instance):
    schedule=solve(instance,2).model_dump()
    citation={"document_id":"regles_reglage","page":1,"element_id":"parametres","version":"1.0","excerpt":"ALU vers ACIER : 30 minutes."}
    class Response:
        ok=True
        status_code=200
        def __init__(self,payload):self.payload=payload
        def json(self):return self.payload
    def request(method,url,**kwargs):
        if url.endswith("/health"):return Response({"model_mode":"ocr","retrieval_mode":"local"})
        if "/drafts/" in url:return Response({"id":"draft","hash":"a"*64,"payload":{"instance":instance.model_dump(),"schedule":schedule}})
        raise AssertionError("Appel inattendu : "+url)
    monkeypatch.setattr("requests.request",request)
    app=AppTest.from_file(str(ROOT/"src/ui/app.py"),default_timeout=15)
    app.session_state["token"]="test-session"
    app.session_state["user"]={"id":"chef","role":"chef","workshop":"ATELIER-1"}
    app.session_state["baseline_id"]="draft"
    app.session_state["active_draft_id"]="draft"
    app.session_state["active_instance"]=instance.model_dump()
    app.session_state["result"]={"answer":"Planning vérifié","schedule":schedule,"diff":{"moved_count":0},"citations":[citation]}
    app.session_state["document_answer"]={"answer":"ALU vers ACIER : 30 minutes.","citations":[citation]}
    app.run()
    assert not app.exception,[e.message for e in app.exception]
