import io
import json
import pytest
from PIL import Image
from src.config import DATA
from src.rag.retriever import Retriever
from src.ingestion.pdf_parser import parse_erp,extract_pdf,bounded_image
from src.llm.client import analyze_image
from src.mcp_server.client import Budget


@pytest.fixture(scope="module")
def retriever():
    return Retriever(memory=True)


def test_retrieval_acl_and_real_citation(retriever,chef):
    hits=retriever.search("SECRET-ATELIER-2 TOUR-Z",chef)
    assert all(p["workshop_id"]=="ATELIER-1" for p in hits)
    assert not any("SECRET-ATELIER-2" in p["text"] for p in hits)
    citations=[retriever.citation(p) for p in hits]
    assert retriever.verify_citations(citations,chef)
    citations[0]["excerpt"]="invented claim"
    assert not retriever.verify_citations(citations,chef)


def test_retrieval_changeover(retriever,chef):
    hits=retriever.search("Quel changement de série ALU vers ACIER ?",chef)
    assert any(p["document_id"]=="regles_reglage" and p["page"]==1 for p in hits)


@pytest.mark.parametrize("extension",[".csv",".xlsx"])
def test_erp_import(extension):
    rows=parse_erp((DATA/"erp"/("orders"+extension)).read_bytes(),extension)
    assert len(rows)==8 and rows[0].duration==65


@pytest.mark.parametrize("quantity",[0,-1,1.5])
def test_erp_rejects_bad_quantity(quantity):
    data=f"id,reference,quantity,due,release,priority\nOF-101,REF-101,{quantity},360,0,1\n".encode()
    with pytest.raises(ValueError):parse_erp(data,".csv")


def test_pdf_text_layer():
    pages=extract_pdf((DATA/"corpus/regles_reglage.pdf").read_bytes())
    assert len(pages)==2 and "30 minutes" in pages[0]["text"]


def test_ocr_machine_and_unknown_duration():
    result=analyze_image((DATA/"sample_images/afficheur_cnc_b.png").read_bytes())
    assert result["observation"]["machine_id"]=="CNC-B"
    assert result["observation"]["downtime_minutes"] is None
    assert result["needs_validation"]


def test_ocr_order_fields():
    result=analyze_image((DATA/"sample_images/ordre_OF_109.png").read_bytes())
    assert result["observation"]["id"]=="OF-109"
    assert result["observation"]["quantity"]==12
    assert result["observation"]["due"]==330


def test_ambiguous_photo():
    result=analyze_image((DATA/"sample_images/illisible.png").read_bytes())
    assert result["observation"]["kind"]=="unknown" and result["needs_validation"]


def test_injection_ocr_not_an_order():
    result=analyze_image((DATA/"sample_images/injection.png").read_bytes())
    assert result["needs_validation"]
    # Selon les langues OCR, le zéro peut rester illisible ; les deux cas bloquent le calcul.
    assert result["observation"].get("quantity") in (0,None)
    assert "proposed_action" not in result


def test_budgets():
    budget=Budget()
    for _ in range(3):budget.consume_mcp()
    with pytest.raises(RuntimeError):budget.consume_mcp()
    for _ in range(6):budget.consume_model()
    with pytest.raises(RuntimeError):budget.consume_model()
    budget.started-=61
    with pytest.raises(TimeoutError):budget.check()


def test_image_limits():
    with pytest.raises(ValueError):bounded_image(b"x"*(8*1024*1024+1))
    image=Image.new("RGB",(5000,4000))
    buffer=io.BytesIO();image.save(buffer,format="PNG")
    with pytest.raises(ValueError):bounded_image(buffer.getvalue())


def test_dataset_split_and_annotation_integrity():
    manifest=json.loads((DATA/"training/manifest.json").read_text())
    rows=[json.loads(line) for line in (DATA/"training/triplets.jsonl").read_text().splitlines()]
    assert len(rows)==1000
    parts=manifest["documents"]
    assert not set(parts["train"])&set(parts["test"])
    assert all(r["positive_document_id"]!=r["negative_document_id"] and r["expert_verified"] is False for r in rows)
