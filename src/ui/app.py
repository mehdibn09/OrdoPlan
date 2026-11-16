"""Client Streamlit : aucune logique d'autorisation ni d'optimisation côté interface."""
import json
import os
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="OrdoPlan · Atelier", page_icon="◷", layout="wide")
API = os.getenv("API_URL", "http://127.0.0.1:8000")
ROOT = Path(__file__).resolve().parents[2]
st.markdown("""<style>
.stApp {background:#f5f7fa;} .block-container {padding-top:2rem;}
h1,h2,h3 {color:#153b4a;} [data-testid="stMetric"] {background:white;border:1px solid #dbe4ea;border-radius:12px;padding:16px;}
[data-testid="stSidebar"] {background:#e9f0f4;} .hero {border-radius:16px;background:#163e4d;color:#fff;padding:26px 32px;margin-bottom:24px;}
.hero h1{color:white;margin:0;font-size:2.5rem;} .hero p{color:#c5e2e7;margin:5px 0 0;}
</style>""", unsafe_allow_html=True)


def call(method, path, **kwargs):
    headers = {"Authorization": "Bearer "+st.session_state.get("token", "")}
    try:
        response = requests.request(method, API+path, headers=headers, timeout=65, **kwargs)
        if not response.ok:
            try:
                message = response.json().get("detail", response.text)
            except ValueError:
                message = response.text[:500]
            st.error(f"{response.status_code} · {message}")
            return None
        return response.json()
    except requests.RequestException:
        st.error("L'API n'est pas joignable. Lancez OrdoPlan avec le script de démarrage.")
        return None


def hhmm(minute):
    value = 480+int(minute)
    return f"{value//60%24:02d}:{value%60:02d}"+(f" J+{value//1440}" if value>=1440 else "")


def gantt(schedule, instance=None, key="gantt-planning"):
    ops = schedule.get("operations", [])
    if not ops:
        return
    fig = go.Figure()
    colors = {"CNC-A": "#0f8b8d", "CNC-B": "#3970bb", "TOUR-C": "#976fc0"}
    for p in ops:
        if p["setup"]:
            fig.add_trace(go.Bar(y=[p["machine"]], x=[p["setup"]], base=[p["start"]-p["setup"]], orientation="h", marker_color="#c9d2de", name="Réglage", text=[""], showlegend=False, hovertemplate=f"Réglage {p['setup']} min<extra></extra>"))
        fig.add_trace(go.Bar(y=[p["machine"]], x=[p["end"]-p["start"]], base=[p["start"]], orientation="h", marker_color=colors.get(p["machine"], "#0f8b8d"), marker_line_color="white", marker_line_width=2, text=[p["order_id"]], textposition="inside", insidetextanchor="middle", name=p["order_id"], showlegend=False, hovertemplate=f"{p['order_id']} · {p['machine']}<br>{hhmm(p['start'])} → {hhmm(p['end'])}<br>Réglage {p['setup']} min<extra></extra>"))
    end = max(480, schedule.get("makespan", 480)+30)
    fig.update_layout(barmode="overlay", height=290, margin=dict(l=10,r=10,t=20,b=10), paper_bgcolor="white", plot_bgcolor="white", font_color="#294757", xaxis=dict(range=[0,end], tickmode="array", tickvals=list(range(0,end+1,60)), ticktext=[hhmm(t) for t in range(0,end+1,60)], gridcolor="#edf1f5", title="Journée fictive · réglages en gris"), yaxis=dict(autorange="reversed", title=""))
    if instance:
        for machine in instance.get("machines", []):
            for w in machine.get("unavailable", []):
                fig.add_vrect(x0=w["start"],x1=w["end"],fillcolor="#e55c5c",opacity=.12,line_width=0,annotation_text="Indisponibilité "+machine["id"],annotation_position="top left")
    st.plotly_chart(fig, width="stretch", key=key)


def show_answer(result, key_prefix="plan"):
    if not result:
        return
    st.markdown(result["answer"])
    if result.get("clarification_question"):
        st.info(result["clarification_question"])
    for uncertainty in result.get("uncertainties", []):
        st.caption("À confirmer : "+uncertainty)
    schedule = result.get("schedule")
    if schedule and schedule.get("operations"):
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Retard pondéré", f"{schedule['weighted_tardiness']} min")
        c2.metric("Fin de journée", hhmm(schedule["makespan"]))
        c3.metric("OF déplacés", result.get("diff", {}).get("moved_count", 0))
        c4.metric("Calcul", f"{schedule['elapsed_seconds']:.2f} s")
        gantt(schedule, st.session_state.get("active_instance"))
        frame = pd.DataFrame(schedule["operations"])
        display = frame.copy()
        for col in ["start", "end"]:
            display[col] = display[col].map(hhmm)
        st.dataframe(display.rename(columns={"order_id":"OF","machine":"Machine","start":"Début","end":"Fin","setup":"Réglage (min)"}), hide_index=True, width="stretch")
        a,b = st.columns(2)
        a.download_button("Exporter le planning CSV", frame.to_csv(index=False), "planning_ordoplan.csv", "text/csv")
        b.download_button("Exporter le résultat JSON", json.dumps(result, ensure_ascii=False, indent=2), "resultat_ordoplan.json", "application/json")
    citations = result.get("citations", [])
    if citations:
        with st.expander(f"Sources vérifiables · {len(citations)} références"):
            for c in citations:
                st.markdown(f"**{c['document_id']} · page {c['page']} · {c['element_id']} · v{c['version']}**")
                st.caption(c["excerpt"])
                if st.button("Ouvrir ce PDF", key=key_prefix+"-doc-"+c["document_id"]+str(c["page"])+c["element_id"]):
                    r = requests.get(f"{API}/documents/{c['document_id']}/{c['page']}", headers={"Authorization":"Bearer "+st.session_state.token}, timeout=15)
                    if r.ok:
                        st.download_button("Télécharger le PDF",r.content,c["document_id"]+".pdf", "application/pdf", key=key_prefix+"-download-"+c["document_id"]+c["element_id"])
    with st.expander("Trace et versions de l'exécution"):
        st.write(" → ".join(result.get("trace", [])))
        st.json(result.get("versions", {}))


with st.sidebar:
    st.markdown("## ◷ OrdoPlan")
    st.caption("L'atelier, dans le bon ordre.")
    if "token" not in st.session_state:
        with st.form("login"):
            username = st.text_input("Identifiant", "chef")
            password = st.text_input("Mot de passe", "OrdoPlan-demo-2026!", type="password")
            if st.form_submit_button("Se connecter", type="primary"):
                result = call("POST", "/auth/login", json={"username":username,"password":password})
                if result:
                    st.session_state.token = result["access_token"]
                    st.session_state.user = result["user"]
                    st.rerun()
        st.caption("Comptes de démonstration : chef, planif, lecture, chef2. Mot de passe commun prérempli.")
    else:
        user = st.session_state.user
        st.markdown(f"**{user['id']}** · {user['role']}")
        st.caption(user["workshop"])
        if st.button("Se déconnecter"):
            call("POST", "/auth/logout")
            st.session_state.clear(); st.rerun()
        st.divider()
        st.caption("Données entièrement fictives. Le solveur calcule ; les sources justifient ; le chef approuve.")
        health = call("GET", "/health")
        if health:
            st.caption(f"Lecture : {health['model_mode']} · recherche : {health['retrieval_mode']}")

st.markdown('<div class="hero"><h1>OrdoPlan</h1><p>Planifier. Comprendre. Valider.</p></div>', unsafe_allow_html=True)
if "token" not in st.session_state:
    st.subheader("Votre journée de production, sous contrôle")
    st.write("Calculez un planning vérifié, comparez l'effet d'une panne ou d'une urgence et préparez sa publication dans le MES.")
    st.info("Connectez-vous dans le panneau de gauche pour ouvrir l'atelier fictif.")
    st.stop()

workshop = st.session_state.user["workshop"]
tabs = st.tabs(["Atelier & planning", "Assistant documentaire", "Documents & photos", "Validation MES", "Évaluation & guide"])

with tabs[0]:
    st.subheader("Une décision appuyée sur les contraintes")
    a,b = st.columns([1,1])
    with a:
        instance = st.selectbox("Instance d'atelier", ["demo"]+[f"instance-{i:02d}" for i in range(50)] if workshop == "ATELIER-1" else ["demo"])
    with b:
        st.caption("2 centres CNC · familles ALU / ACIER · 8 OF · outillage partagé")
        if st.session_state.get("import_id"):
            use_import = st.checkbox("Utiliser le dernier export ERP importé", value=True)
        else:
            use_import = False
    if st.button("Calculer le planning initial", type="primary", disabled=st.session_state.user["role"] == "lecteur"):
        with st.spinner("Lecture ERP via MCP, optimisation et contrôle indépendant…"):
            body = {"mode":"plan","workshop_id":workshop,"instance_id":instance,"question":"Planning initial selon les gammes, changements de série et outillage unique."}
            if use_import:
                body["import_id"] = st.session_state.import_id
            result = call("POST", "/assistant", json=body)
            if result:
                st.session_state.result = result
                if result.get("proposed_action"):
                    st.session_state.baseline_id = result["proposed_action"]["draft_id"]
                    st.session_state.active_draft_id = st.session_state.baseline_id
                    draft = call("GET", "/drafts/"+st.session_state.baseline_id)
                    if draft:
                        st.session_state.active_instance = draft["payload"]["instance"]
    if st.session_state.get("baseline_id"):
        with st.expander("Replanifier après un aléa", expanded=False):
            with st.form("event"):
                c1,c2,c3 = st.columns(3)
                kind = c1.selectbox("Aléa", ["Panne machine", "Commande urgente OF-109", "Retard matière"])
                minute = c2.number_input("Début · minutes depuis 08:00", min_value=0, max_value=720, value=150, step=5)
                duration = c3.number_input("Durée · minutes", min_value=1,max_value=720,value=180,step=5)
                machine = c1.selectbox("Machine concernée", ["CNC-B","CNC-A"])
                order = c2.text_input("OF pour retard matière", "OF-107")
                confirmed = st.checkbox("J'ai confirmé l'instant, la durée et la machine de l'aléa")
                if st.form_submit_button("Recalculer et comparer", disabled=st.session_state.user["role"] == "lecteur"):
                    if not confirmed:
                        st.info("Confirmez les champs de l'aléa avant le calcul.")
                    else:
                        event = {"kind":{"Panne machine":"breakdown","Commande urgente OF-109":"urgent","Retard matière":"material_delay"}[kind],"start":minute,"duration":duration,"machine_id":machine,"order_id":order}
                        with st.spinner("Replanification des opérations futures…"):
                            result = call("POST","/assistant",json={"mode":"plan","workshop_id":workshop,"baseline_draft_id":st.session_state.baseline_id,"event":event,"question":"Expliquer les écarts et les retards après aléa."})
                        if result:
                            st.session_state.result = result
                            if result.get("proposed_action"):
                                st.session_state.active_draft_id = result["proposed_action"]["draft_id"]
                                st.session_state.baseline_id = st.session_state.active_draft_id
                                draft = call("GET","/drafts/"+st.session_state.active_draft_id)
                                if draft:
                                    st.session_state.active_instance = draft["payload"]["instance"]
    show_answer(st.session_state.get("result"))

with tabs[1]:
    st.subheader("Une réponse, ses preuves")
    with st.form("question"):
        question = st.text_area("Question sur les gammes et les règles", "Quel est le temps de changement de série ALU vers ACIER ?")
        if st.form_submit_button("Rechercher dans mes documents", type="primary"):
            with st.spinner("Recherche hybride et vérification des références…"):
                st.session_state.document_answer = call("POST","/assistant",json={"workshop_id":workshop,"mode":"question","question":question})
    show_answer(st.session_state.get("document_answer"),key_prefix="document")

with tabs[2]:
    left,right = st.columns(2)
    with left:
        st.subheader("Lire un export ERP")
        erp = st.file_uploader("Carnet de commandes CSV ou Excel",type=["csv","xlsx"], key="erp")
        if st.button("Valider et importer l'export",disabled=not erp):
            result = call("POST","/imports/erp",files={"file":(erp.name,erp.getvalue())})
            if result:
                st.session_state.import_id = result["import_id"]
                st.success(f"{len(result['orders'])} OF validés. Export disponible dans l'onglet planning.")
                st.dataframe(pd.DataFrame(result["orders"])[["id","reference","quantity","due","release","priority"]],hide_index=True)
        st.subheader("Extraire un PDF")
        pdf = st.file_uploader("Ordre papier ou document PDF",type=["pdf"])
        if st.button("Extraire le contenu PDF",disabled=not pdf):
            result = call("POST","/imports/pdf",files={"file":(pdf.name,pdf.getvalue())})
            if result:
                st.json(result)
    with right:
        st.subheader("Lire une photographie")
        image = st.file_uploader("Afficheur ou ordre de fabrication",type=["png","jpg","jpeg","webp"])
        sample = st.selectbox("Ou choisir une image de démonstration",["—","afficheur_cnc_b.png","ordre_OF_109.png","illisible.png","injection.png"])
        if st.button("Analyser la photographie", type="primary",disabled=not image and sample=="—"):
            content = image.getvalue() if image else (ROOT/"data/sample_images"/sample).read_bytes()
            st.image(content,width=450)
            with st.spinner("Lecture locale et recherche de champs…"):
                st.session_state.image_result = call("POST","/analyze",files={"file":(image.name if image else sample,content)})
        if st.session_state.get("image_result"):
            result = st.session_state.image_result
            st.json(result["observation"])
            for u in result["uncertainties"]:
                st.info(u)
            with st.expander("Lecture OCR et VLM"):
                st.text(result["ocr"])
                st.write(result.get("vlm"))
            st.caption("Pour une panne, confirmez les champs dans le formulaire d'aléa. Pour un OF, vérifiez puis importez un export ERP conforme. La photo ne publie aucun planning.")

with tabs[3]:
    st.subheader("Le planning exact, puis votre accord")
    draft_id = st.text_input("Identifiant du brouillon",st.session_state.get("active_draft_id", ""))
    if draft_id:
        draft = call("GET","/drafts/"+draft_id)
        if draft:
            st.caption("Empreinte du contenu : "+draft["hash"])
            gantt(draft["payload"]["schedule"],draft["payload"]["instance"],key="gantt-validation")
            st.dataframe(pd.DataFrame(draft["payload"]["schedule"]["operations"]),hide_index=True)
            agreement = st.checkbox("J'ai vérifié ce planning exact et j'approuve sa publication dans le MES de démonstration")
            a,b,c = st.columns(3)
            if a.button("Approuver ce contenu",disabled=not agreement or st.session_state.user["role"] != "chef",type="primary"):
                approved = call("POST",f"/drafts/{draft_id}/approve",json={"hash":draft["hash"],"confirmed":True})
                if approved:
                    st.session_state.approval = {"draft_id":draft_id, "token":approved["approval_token"]}
                    st.success("Accord enregistré pour 5 minutes. La publication reste à déclencher.")
            approved = st.session_state.get("approval", {})
            if b.button("Publier dans le MES",disabled=approved.get("draft_id") != draft_id):
                published = call("POST",f"/drafts/{draft_id}/publish",json={"approval_token":approved["token"]})
                if published:
                    st.success(f"Planning publié · version MES {published['publication_id']}")
            if c.button("Annuler le brouillon"):
                result = call("POST",f"/drafts/{draft_id}/cancel")
                if result:
                    st.success("Brouillon annulé")
    st.divider()
    if st.button("Consulter l'historique MES"):
        st.session_state.history = call("GET","/publications")
    if st.session_state.get("history"):
        st.dataframe(pd.DataFrame(st.session_state.history),hide_index=True)
        pub_id = st.number_input("Version à restaurer",min_value=1,step=1)
        if st.button("Préparer un retour à cette version"):
            result = call("POST",f"/publications/{pub_id}/rollback-draft")
            if result:
                st.session_state.active_draft_id = result["id"]
                st.info("Nouveau brouillon : "+result["id"]+". Une nouvelle approbation est requise.")

with tabs[4]:
    st.subheader("Un prototype mesuré et reproductible")
    st.write("Le dépôt contient 40 documents fictifs, 50 instances, les données d'adaptation, les scénarios d'évaluation et les résultats observés. Les résultats CPU ne constituent pas un benchmark GPU ou industriel.")
    for name in ["evaluation.json","retrieval_metrics.json","neural_reranker_metrics.json"]:
        path = ROOT/"reports"/name
        if path.exists():
            with st.expander(name):
                st.json(json.loads(path.read_text()))
    st.markdown("**Parcours de démonstration** : planning initial → panne confirmée → urgence → comparaison → approbation → publication → ambiguïté → accès refusé.")
    st.caption("Si une panne chevauche une opération gelée, le modèle signale une impossibilité. Le chef doit alors préciser la suspension réelle de l'opération : le prototype ne l'invente pas.")
    if st.button("Créer un code d'association Telegram"):
        result = call("POST","/telegram/link-code")
        if result:
            st.code("/link "+result["code"])
            st.caption("À envoyer au bot configuré dans les 5 minutes.")
