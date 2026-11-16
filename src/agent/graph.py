"""Workflow LangGraph borné, interruptions humaines persistées et chiffrées."""
import asyncio
import base64
import json
import time
from importlib.metadata import version
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langgraph.types import interrupt
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.serde.encrypted import EncryptedSerializer
from langchain_core.prompts import ChatPromptTemplate
from src.config import DATA
from src.schemas.pydantic_models import Answer, Instance, Order, Schedule
from src.solver.cp_sat import solve
from src.solver.checker import check_schedule, diff_schedules
from src.agent.guardrails import suspicious, unsafe_request
from src.mcp_server.client import MCPClient, Budget
from src.rag.retriever import get_retriever
from src.reranker.reranker_service import tokens
from src.llm.prompts import load_prompt


@dataclass
class RunContext:
    user: dict
    token: str
    store: object
    budget: Budget
    approval_token: str = ""


context = ContextVar("ordoplan_run_context")


class AgentState(TypedDict, total=False):
    request: dict
    actor: str
    instance: dict
    schedule: dict
    answer: dict
    sources: list[dict]
    tools: list[dict]
    trace: list[str]
    draft: dict
    publication: dict


VERSIONS = {"application": "1.0.0", "prompt": "v1", "reranker": "local-v1", "index": "corpus-v1", "model": "ocr+explanation-templates", "solver": "ortools-"+version("ortools"), "instance_schema": "v1"}


def hhmm(minutes):
    total = 8*60+minutes
    day = total//1440
    return f"{total//60%24:02d}:{total%60:02d}" + (f" J+{day}" if day else "")


def step(state, name, **updates):
    context.get().budget.check()
    return {"trace": state.get("trace", [])+[name], **updates}


def stopped(status, answer, question=None, uncertainties=None):
    return Answer(status=status, answer=answer, clarification_question=question, uncertainties=uncertainties or [], versions=VERSIONS).model_dump()


def verify_access(state):
    ctx = context.get()
    req = state["request"]
    ctx.store.access(ctx.user, req["workshop_id"])
    if ctx.user["id"] != state["actor"]:
        raise PermissionError("La reprise appartient à un autre utilisateur")
    if unsafe_request(req.get("question", "")):
        return step(state, "access_refused", answer=stopped("refused", "OrdoPlan ne pilote pas les machines. Consultez le responsable habilité."))
    if suspicious(req.get("question", "")):
        return step(state, "untrusted_instruction_ignored", answer=stopped("refused", "Cette instruction ne peut pas modifier les contraintes ni déclencher une publication. Utilisez le formulaire et l'approbation du chef d'atelier."))
    if req["mode"] == "plan" and ctx.user["role"] == "lecteur":
        raise PermissionError("Préparation réservée au planificateur et au chef")
    return step(state, "verify_access")


async def load_orders(state):
    ctx = context.get()
    req = state["request"]
    if req["mode"] == "question":
        return step(state, "document_query")
    client = MCPClient(ctx.token, ctx.budget)
    payload = await client.call("get_open_orders", {"workshop_id": req["workshop_id"]})
    tools = [{"tool": "get_open_orders", "workshop_id": req["workshop_id"], "count": len(payload["orders"])}]
    instance_id = req.get("instance_id", "demo")
    if instance_id != "demo":
        # Une liste fermée exclut toute traversée de chemin.
        valid = {f"instance-{i:02d}" for i in range(50)}
        if instance_id not in valid or ctx.user["workshop"] != "ATELIER-1":
            raise PermissionError("Instance inaccessible")
        payload = json.loads((DATA/"instances"/f"{instance_id}.json").read_text())
    if req.get("import_id"):
        with ctx.store.db() as db:
            row = db.execute("SELECT * FROM imports WHERE id=?", (req["import_id"],)).fetchone()
        if not row:
            raise KeyError("Import introuvable")
        ctx.store.access(ctx.user, row["workshop"])
        payload["orders"] = ctx.store.decode(row["payload"])
    if req.get("baseline_draft_id"):
        old = ctx.store.get_draft(ctx.user, req["baseline_draft_id"])
        payload = old["payload"]["instance"]
        payload["baseline"] = old["payload"]["schedule"]["operations"]
    instance = Instance.model_validate(payload)
    accessible = {p["document_id"] for p in get_retriever().allowed(ctx.user)}
    parameter_sources = {instance.setup_source.document_id, *(s.document_id for o in instance.orders for s in o.sources.values()), *(m.source.document_id for m in instance.machines)}
    external = {s for s in parameter_sources if s.startswith("erp_instance_") and ctx.user["workshop"] == "ATELIER-1"}
    for sid in parameter_sources:
        if sid.startswith("erp_import_"):
            with ctx.store.db() as db:
                imported = db.execute("SELECT workshop FROM imports WHERE id=?", (sid.removeprefix("erp_import_"),)).fetchone()
            if imported and imported["workshop"] == ctx.user["workshop"]:
                external.add(sid)
    missing = parameter_sources-accessible-external
    if missing:
        return step(state, "missing_parameter_sources", answer=stopped("needs_clarification", "Des paramètres n'ont pas de source accessible dans cet atelier.", "Fournissez des gammes et exports autorisés pour cet atelier.", ["Sources manquantes ou inaccessibles : "+", ".join(sorted(missing))]))
    event = req.get("event")
    if event:
        if not instance.baseline:
            return step(state, "missing_baseline", answer=stopped("needs_clarification", "Un aléa doit être comparé à un planning calculé.", "Calculez d'abord un planning initial, puis sélectionnez-le comme référence."))
        instance.now = event["start"]
        instance.frozen = [p for p in instance.baseline if p.start-p.setup < instance.now]
        kind = event["kind"]
        if kind == "breakdown":
            if event.get("duration") is None:
                return step(state, "unknown_downtime", answer=stopped("needs_clarification", "La durée de panne n'est pas établie : aucun recalcul fiable n'est lancé.", "Quelle durée d'arrêt faut-il retenir ?"))
            mid = event.get("machine_id")
            machine = next((m for m in instance.machines if m.id == mid), None)
            if not machine:
                raise ValueError("Machine inconnue")
            status = await client.call("get_machine_status", {"machine_id": mid})
            tools.append({"tool": "get_machine_status", **status})
            from src.schemas.pydantic_models import Window
            machine.unavailable.append(Window(start=event["start"], end=event["start"]+event["duration"]))
        elif kind == "urgent":
            urgent = Order.model_validate_json((DATA/"synthetic/urgent_order.json").read_text())
            if any(o.id == urgent.id for o in instance.orders):
                raise ValueError("OF-109 déjà présent")
            urgent.release = max(urgent.release, event["start"])
            instance.orders.append(urgent)
        elif kind == "material_delay":
            order = next((o for o in instance.orders if o.id == event.get("order_id")), None)
            if not order or not event.get("duration"):
                raise ValueError("OF ou durée manquant")
            order.release = event["start"]+event["duration"]
        instance.id += "-"+kind
    # Les notes et les textes OCR ne sont jamais interprétés comme paramètres.
    return step(state, "read_erp_and_validate_fields", instance=instance.model_dump(), tools=tools)


def retrieve(state):
    ctx = context.get()
    query = state["request"]["question"] or "règles ordonnancement changement de série outillage"
    retriever = get_retriever()
    sources = retriever.chain.invoke({"query": query, "user": ctx.user, "limit": 5})
    if state["request"]["mode"] == "plan":
        sources = [p for p in sources if p["page"] == 1]
        # Les sources des paramètres sont récupérées explicitement et soumises aux mêmes ACL.
        instance = Instance.model_validate(state["instance"])
        needed = {instance.setup_source.document_id, *(s.document_id for o in instance.orders for s in o.sources.values())}
        for p in retriever.allowed(ctx.user):
            if p["document_id"] in needed and p["page"] == 1 and not any(retriever.key(p) == retriever.key(q) for q in sources):
                sources.append(p)
    return step(state, "hybrid_retrieval_rrf_reranking", sources=sources)


async def optimize(state):
    if state["request"]["mode"] != "plan":
        return step(state, "skip_solver_document_question")
    instance = Instance.model_validate(state["instance"])
    remaining = 59-(time.monotonic()-context.get().budget.started)
    result = await asyncio.to_thread(solve, instance, max(.05, min(20, remaining)))
    return step(state, "solve_cp_sat", schedule=result.model_dump())


def validate(state):
    if "schedule" in state:
        instance = Instance.model_validate(state["instance"])
        schedule = Schedule.model_validate(state["schedule"])
        if schedule.operations:
            errors = check_schedule(instance, schedule.operations)
            if errors:
                raise ValueError("Contrôleur indépendant : " + "; ".join(errors))
    return step(state, "independent_constraint_check")


def explain(state):
    ctx = context.get()
    retriever = get_retriever()
    citations = [retriever.citation(p) for p in state["sources"]]
    if not retriever.verify_citations(citations, ctx.user):
        raise PermissionError("Citation inaccessible ou modifiée")
    if state["request"]["mode"] == "question":
        query_tokens = tokens(state["request"]["question"]) - {"le", "la", "les", "de", "des", "du", "une", "un", "est", "et", "pour", "quel", "quelle", "quels", "comment", "sur", "a", "en", "dans"}
        supported = [p for p in state["sources"] if len(query_tokens & tokens(p["text"]+" "+p["title"])) >= 1 and p["element_id"] != "tracabilite"]
        if not supported:
            answer = stopped("needs_clarification", "Aucune source accessible ne soutient cette demande.", "Précisez la machine et la règle recherchée ou fournissez un document autorisé.")
        else:
            p = supported[0]
            # Réponse extractive : chaque affirmation provient du passage cité.
            answer = Answer(status="answered", answer=p["text"], citations=[retriever.citation(p)], versions=VERSIONS).model_dump()
        return step(state, "verify_documentary_evidence", answer=answer)
    instance = Instance.model_validate(state["instance"])
    schedule = Schedule.model_validate(state["schedule"])
    if not schedule.operations:
        status = "infeasible" if schedule.status == "INFEASIBLE" else "needs_clarification"
        text = "Aucun planning réalisable dans cet horizon." if status == "infeasible" else "Le solveur n'a pas trouvé de solution dans le budget disponible."
        answer = Answer(status=status, answer=text, uncertainties=schedule.violations, clarification_question="Vérifiez les opérations gelées pendant la panne, l'horizon, les disponibilités matière et ressources. Quel assouplissement autorisez-vous ?", schedule=schedule, tool_results=state.get("tools", []), versions=VERSIONS).model_dump()
        return step(state, "report_solver_status", answer=answer)
    delta = diff_schedules(instance.baseline, schedule.operations, instance)
    quality = "Optimalité lexicographique démontrée" if schedule.status == "OPTIMAL" else "Meilleure solution trouvée dans le temps imparti"
    facts = {"quality": quality, "late": len(delta["delays"]), "weighted": schedule.weighted_tardiness, "end": hhmm(schedule.makespan), "moved": delta["moved_count"]}
    template = ChatPromptTemplate.from_template(load_prompt("explain_schedule_v1")["template"])
    text = template.format_messages(**facts)[0].content
    for d in delta["delays"]:
        text += f" {d['order_id']} : retard de {d['minutes']} minutes."
    # Les nombres sont construits exclusivement depuis Schedule et diff_schedules.
    action = None
    draft = None
    if state["request"].get("prepare", True):
        draft = ctx.store.prepare(ctx.user, instance.workshop_id, {"instance": instance.model_dump(), "schedule": schedule.model_dump(), "request_id": state["request"]["request_id"]})
        action = {"type": "publish_schedule", "draft_id": draft["id"], "hash": draft["hash"], "approval_required": True, "thread_id": state["request"]["request_id"]}
    answer = Answer(status="proposed", answer=text, schedule=schedule, diff=delta, citations=citations, proposed_action=action, tool_results=state.get("tools", []), versions=VERSIONS).model_dump()
    return step(state, "explain_and_verify_computed_facts", answer=answer, draft=draft)


def await_approval(state):
    # Ce nœud est repris avec une session fraîche ; aucun secret n'est dans l'état persisté.
    ctx = context.get()
    if ctx.user["id"] != state["actor"] and ctx.user["role"] != "chef":
        raise PermissionError("Reprise non autorisée")
    approved = interrupt({"draft_id": state["draft"]["id"], "hash": state["draft"]["hash"], "message": "Attente de l'approbation du planning exact"})
    if not approved.get("approved") or approved.get("hash") != state["draft"]["hash"]:
        raise PermissionError("Reprise sans accord sur le contenu exact")
    return step(state, "human_approval_received")


async def publish(state):
    ctx = context.get()
    d = ctx.store.get_draft(ctx.user, state["draft"]["id"])
    result = await MCPClient(ctx.token, ctx.budget).call("publish_schedule", {"workshop_id": d["workshop_id"], "schedule_id": d["id"], "approval_token": ctx.approval_token})
    return step(state, "publish_via_mcp", publication=result)


async def build_graph(store):
    graph = StateGraph(AgentState)
    for name, node in [("access", verify_access), ("load", load_orders), ("retrieve", retrieve), ("solve", optimize), ("check", validate), ("explain", explain), ("approval", await_approval), ("publish", publish)]:
        graph.add_node(name, node)
    graph.set_entry_point("access")
    graph.add_conditional_edges("access", lambda s: END if s.get("answer") else "load")
    graph.add_conditional_edges("load", lambda s: END if s.get("answer") else "retrieve")
    graph.add_edge("retrieve", "solve")
    graph.add_edge("solve", "check")
    graph.add_edge("check", "explain")
    graph.add_conditional_edges("explain", lambda s: "approval" if s.get("draft") else END)
    graph.add_edge("approval", "publish")
    graph.add_edge("publish", END)
    key = base64.urlsafe_b64decode((store.path.parent/"storage.key").read_bytes())
    serializer = EncryptedSerializer.from_pycryptodome_aes(key=key)
    import aiosqlite
    connection = await aiosqlite.connect(store.path.parent/"checkpoints.sqlite3")
    saver = AsyncSqliteSaver(connection, serde=serializer)
    await saver.setup()
    return graph.compile(checkpointer=saver), connection
