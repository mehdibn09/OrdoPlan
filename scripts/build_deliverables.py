"""Rapport PDF/DOCX, figures et support PPTX/PDF, calculés depuis les rapports réels.

Utilise les bibliothèques documentaires de requirements-docs.txt.
"""
import json
import os
import re
import textwrap
from pathlib import Path
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.getenv("ORDOPLAN_DELIVERABLES_DIR",str(ROOT/"livrables")))


def read(name):
    return json.loads((ROOT/"reports"/name).read_text())


def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding="utf-8")


def generate_narratives():
    e=read("evaluation.json");n=read("neural_reranker_metrics.json");d=read("end_to_end.json")
    tests=ET.parse(ROOT/"reports/unit-tests.xml").getroot()
    test_count=len(tests.findall(".//testcase"))
    intro=f"""# Rapport de réalisation — OrdoPlan

Projet intégrateur d'IA générative multimodale et agentique. Version livrée 1.0.0, 16 novembre 2026.

## Résumé exécutif

OrdoPlan est un prototype fonctionnel d'aide à l'ordonnancement d'un atelier fictif. Il lit un carnet ERP, consulte des documents autorisés, calcule un planning par CP-SAT, vérifie indépendamment les contraintes, explique les écarts et interrompt le workflow avant toute publication MES. La décision d'ordonnancement appartient au solveur. La lecture documentaire et les observations visuelles n'accordent jamais d'autorisation de publication.

La réalisation couvre API FastAPI, Streamlit/Plotly, LangChain/LangGraph, véritable serveur et client MCP v2, Qdrant, OCR local, VLM ouvert, encodeurs multilingues/CLIP, adaptation réelle d'un cross-encoder, approbation liée au contenu, versions MES et retour arrière. Deux profils permettent un démarrage léger et une expérimentation complète des modèles locaux. Le bot Telegram et son association d'identité sont fournis ; son activation réelle requiert les secrets personnels du propriétaire.

Le dépôt contient 40 PDF synthétiques et 87 passages, 50 instances plus le fil rouge, des CSV/Excel et images, 1 000 triplets séparés par document et 150 scénarios. Les documents industriels, entretiens terrain et annotations expertes n'ont pas été inventés. Les choix et écarts au sujet sont détaillés dans la matrice de conformité et la fiche de limites.

## Vérifications observées

- {test_count} tests unitaires et API réussis dans la suite finale.
- {e['passed']}/{e['executed']} scénarios de composants réussis ; {e['solver']['violations']} contrainte violée dans les {e['solver']['valid_schedules']} plannings de référence.
- Retard pondéré inférieur ou égal à FIFO et EDD dans respectivement {e['solver']['not_worse_than_FIFO']} et {e['solver']['not_worse_than_EDD']} cas sur 30.
- Replanification : p95 du solveur {e['replanning']['p95_seconds']:.3f} s sur 25 aléas synthétiques.
- Les temps de composants ont une médiane de {e['latency_seconds']['median']:.3f} s et un p95 de {e['latency_seconds']['p95']:.3f} s ; ce ne sont pas des latences multi-utilisateurs de production.
- Parcours HTTP + MCP réel réussi, approbation et réessai idempotent vérifiés. Latence p95 de ce parcours de requêtes : {d['latency_seconds']['p95']:.3f} s dans les conditions décrites dans le JSON.
- Embeddings multilingues + CLIP + reranker adapté essayés localement ; le VLM compact a produit des transcriptions insuffisantes et le système maintient la validation humaine.
- Les audits finaux du socle et de l'environnement complet ne signalent pas de vulnérabilité connue au moment de leur exécution ; la CI doit continuer ces contrôles.

## Lecture de ces résultats

L'adaptation du cross-encoder a réellement entraîné {n['trainable_parameters']:,} paramètres pendant {n['elapsed_seconds']:.1f} s sur CPU, une époque, 600 triplets. nDCG@5 et MRR@10 sont identiques avant/après ({n['pretrained']['nDCG@5']:.3f} et {n['adapted']['nDCG@5']:.3f} pour nDCG@5). Aucun gain neuronal n'est démontré. Le jeu à titres explicites manque de difficulté et ne permet pas de généraliser à l'atelier réel.

La suite de 150 cas comprend 10 images OCR, des exports, PDF et rejets, et non 30 lectures VLM de photos industrielles. Les tests du transport, du navigateur et des modèles sont séparés et accompagnés de preuves. Le matériel GPU de 24 Go n'a pas été évalué.
"""
    write(ROOT/"docs/rapport_synthese.md",intro)
    report="""# Résultats expérimentaux détaillés

## Scénarios et validité

| Catégorie | Exécutés | Réussis |
|---|---:|---:|
"""
    for category,count in e["categories"].items():
        passed=sum(r["passed"] for r in e["results"] if r["category"]==category)
        report+=f"| {category} | {count} | {passed} |\n"
    report+="\n## Comparaison des méthodes de recherche\n\n| Configuration | Recall@5 | nDCG@5 | MRR@10 |\n|---|---:|---:|---:|\n"
    for label,m in read("retrieval_metrics.json")["results"].items():report+=f"| {label} | {m['Recall@5']:.4f} | {m['nDCG@5']:.4f} | {m['MRR@10']:.4f} |\n"
    for label in ["pretrained","adapted"]:
        m=n[label];report+=f"| cross-encoder {label} | {m['Recall@5']:.4f} | {m['nDCG@5']:.4f} | {m['MRR@10']:.4f} |\n"
    report+="\nLes comparaisons légères et neuronales emploient le même découpage documentaire, mais des fonctions de score différentes. Les scores parfaits sur ce jeu facile ne constituent pas une preuve de performance générale. Les résultats restent ceux observés, y compris l'absence de progrès après adaptation.\n\n## Parcours fil rouge\n\n"
    for phase in ["initial","breakdown","urgent"]:
        report+=f"### {phase}\n\n{d[phase]['answer']}\n\n| OF | Machine | Début | Fin | Réglage min |\n|---|---|---|---|---:|\n"
        for p in d[phase]["schedule"]["operations"]:
            def hh(t):return f"{8+t//60:02d}:{t%60:02d}"
            report+=f"| {p['order_id']} | {p['machine']} | {hh(p['start'])} | {hh(p['end'])} | {p['setup']} |\n"
    report+="\n## Dossier de preuves\n\nLes JSON conservent les opérations, différences et résultats individuels ; les XML conservent les cas de test exécutés ; les captures montrent l'interface réelle. Les fichiers d'audit décrivent leurs paquets et vulnérabilités connues, pas une garantie absolue de sûreté. Les journaux et jetons locaux ne sont pas redistribués.\n"
    write(ROOT/"docs/resultats_observes.md",report)
    stages=[("V1", "Socle documentaire et RAG", "L1.1 à L1.6", "src/ingestion, src/rag, API et interface", "tests documentaires, index Qdrant et sources accessibles"), ("V2","Multimodalité et adaptation","L2.1 à L2.6","OCR/VLM local, CLIP, dataset et modèles adaptés","smoke tests modèles, scores avant/après et champs à confirmer"), ("V3","Agentique et MCP","L3.1 à L3.6","LangGraph, MCP MES/ERP, solveur et approbation","parcours HTTP/MCP réel et refus des publications non approuvées"), ("V4","Solution intégrée","L4.1 à L4.7","bot, sécurité, déploiement, documentation et soutenance","tests, audits, scénario complet ; Telegram réel à configurer")]
    for version,title,refs,code,proof in stages:
        write(ROOT/f"docs/jalons/{version}.md",f"# {version} — {title}\n\nRéférences : {refs}.\n\nIncrément intégré dans la même application : {code}.\n\nPreuves : {proof}.\n\nCe document décrit la correspondance pédagogique des fonctions de la version finale. Il ne prétend pas qu'une période calendaire d'une semaine a été observée ni qu'un historique Git ancien existe.\n")
    weeks=[("Cadrage, corpus, architecture", "40 PDF fictifs, métadonnées, risques et guide d'entretien non effectué"), ("Solveur et contrôleur", "CP-SAT, ressources, gel, baselines et instances"), ("Ingestion et multimodalité", "CSV/Excel/PDF, OCR, VLM, recherche multilingue et CLIP"), ("Agentique et MCP", "Graphe, interruptions persistées, approbation et MES versionné"), ("Adaptation et évaluation", "1 000 triplets, entraînement ciblé réel, 150 cas et audits"), ("Intégration et soutenance", "Interface, bot, Docker, guides, rapport et support")]
    for i,(title,result) in enumerate(weeks,1):
        write(ROOT/f"compte_rendu_semaine_{i}.md",f"# Lot pédagogique {i} — {title}\n\nTravaux livrés : {result}.\n\nValidation : consulter les preuves et limites correspondantes dans docs/matrice_conformite.md et reports/.\n\nLa réalisation est regroupée dans cette livraison. Ce fichier ne représente ni une semaine calendaire effectivement écoulée ni un entretien fictif.\n")


def figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch
    fig,ax=plt.subplots(figsize=(12,6));ax.axis("off")
    boxes=[(.02,.70,"Streamlit / Telegram\nUtilisateur autorisé"),(.36,.70,"FastAPI\nIdentité et atelier"),(.70,.70,"LangGraph\nÉtat et budgets"),(.02,.34,"Documents / OCR / VLM\nRAG et sources"),(.36,.34,"CP-SAT + contrôleur\nDates et écarts"),(.70,.34,"MCP MES / ERP\nAccord exact requis")]
    for x,y,text in boxes:
        ax.add_patch(FancyBboxPatch((x,y),.27,.18,boxstyle="round,pad=0.01",facecolor="#eef4f7",edgecolor="#235365"))
        ax.text(x+.135,y+.09,text,ha="center",va="center",fontsize=11,color="#163b4a")
    for start,end in [((.29,.79),(.35,.79)),((.63,.79),(.69,.79)),((.835,.69),(.835,.53)),((.70,.70),(.16,.53)),((.76,.70),(.50,.53))]:
        ax.annotate("",xy=end,xytext=start,arrowprops={"arrowstyle":"->","color":"#527384","lw":1.5})
    ax.text(.5,.10,"Le solveur décide · Le contrôleur vérifie · Le chef approuve",ha="center",fontsize=13,color="#163b4a")
    fig.tight_layout();fig.savefig(ROOT/"reports/architecture.png",dpi=160,bbox_inches="tight");plt.close(fig)
    e=read("evaluation.json")
    rows=[r["evidence"] for r in e["results"] if r["category"]=="ordonnancement"]
    fig,ax=plt.subplots(figsize=(11,4))
    for label,color in [("FIFO","#9aa9b7"),("EDD","#4b77b4"),("CP-SAT","#0b898c")]:
        values=[r["solver"]["weighted_tardiness"] if label=="CP-SAT" else r["baselines"][label]["weighted_tardiness"] for r in rows]
        ax.plot(range(1,len(rows)+1),values,label=label,color=color,marker="o",markersize=3)
    ax.set_xlabel("Instance synthétique");ax.set_ylabel("Retard pondéré (minutes)");ax.grid(alpha=.15);ax.legend();fig.tight_layout();fig.savefig(ROOT/"reports/comparaison_solveur.png",dpi=160);plt.close(fig)
    d=read("end_to_end.json")
    for phase in ["initial","breakdown","urgent"]:
        fig,ax=plt.subplots(figsize=(11,3))
        for p in d[phase]["schedule"]["operations"]:
            y=0 if p["machine"]=="CNC-A" else 1
            if p["setup"]:ax.barh(y,p["setup"],left=p["start"]-p["setup"],height=.50,color="#ccd3dc")
            ax.barh(y,p["end"]-p["start"],left=p["start"],height=.50,color="#0b898c" if y==0 else "#4b77b4",edgecolor="white")
            ax.text((p["start"]+p["end"])/2,y,p["order_id"],ha="center",va="center",fontsize=8,color="white")
        ax.set_yticks([0,1],["CNC-A","CNC-B"]);ax.invert_yaxis();ax.set_xlim(0,max(480,d[phase]["schedule"]["makespan"]+20));ticks=list(range(0,int(ax.get_xlim()[1])+1,60));ax.set_xticks(ticks,[f"{8+t//60:02d}:00" for t in ticks]);ax.grid(axis="x",alpha=.15);ax.set_title({"initial":"Planning initial","breakdown":"Après panne confirmée","urgent":"Après arrivée de l'urgence"}[phase]);fig.tight_layout();fig.savefig(ROOT/f"reports/gantt_{phase}.png",dpi=170);plt.close(fig)


def blocks(text):
    lines=text.splitlines();result=[];i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith("```"):
            lang=line[3:];code=[];i+=1
            while i<len(lines) and not lines[i].startswith("```"):code.append(lines[i]);i+=1
            if lang!="mermaid":result.append(("code","\n".join(code)))
        elif line.startswith("#"):
            match=re.match(r"(#+)\s+(.*)",line);result.append(("h"+str(min(3,len(match[1]))),match[2]))
        elif line.startswith("|"):
            table=[]
            while i<len(lines) and lines[i].startswith("|"):
                row=[c.strip().strip('`') for c in lines[i].strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?",v or "-") for v in row):table.append(row)
                i+=1
            result.append(("table",table));continue
        elif line.strip():
            if line.startswith(("- ","1. ","2. ","3. ","4. ","5. ","6. ","7. ","8. ","9. ")):result.append(("bullet",line))
            else:
                paragraph=[line]
                while i+1<len(lines) and lines[i+1].strip() and not lines[i+1].startswith(("#","|","```","- ")):i+=1;paragraph.append(lines[i])
                result.append(("p"," ".join(paragraph)))
        i+=1
    return result


def plain(text):
    text=re.sub(r"\[([^]]+)\]\([^)]+\)",r"\1",text)
    return text.replace("**","").replace("`","")


def documents():
    files=["rapport_synthese.md","cadrage_et_architecture.md","modele_optimisation.md","evaluation_protocole.md","resultats_observes.md","securite.md","installation.md","guide_utilisateur.md","fiche_de_limites.md","matrice_conformite.md","demonstration.md","entretien_atelier.md"]
    if (ROOT/"docs/deploiement_verifie.md").exists():files.insert(7,"deploiement_verifie.md")
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image as RLImage,Preformatted
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("DejaVu","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVuBold","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    pdfmetrics.registerFontFamily("DejaVu",normal="DejaVu",bold="DejaVuBold",italic="DejaVu",boldItalic="DejaVuBold")
    styles=getSampleStyleSheet()
    for name in ["Normal","BodyText","Heading1","Heading2","Heading3"]:styles[name].fontName="DejaVu"
    styles["Normal"].fontSize=9;styles["Normal"].leading=14;styles["Normal"].spaceAfter=7
    styles["Heading1"].fontSize=19;styles["Heading1"].leading=24;styles["Heading1"].textColor=colors.HexColor("#163e4d");styles["Heading1"].spaceAfter=16
    styles["Heading2"].fontSize=12;styles["Heading2"].leading=17;styles["Heading2"].spaceBefore=12;styles["Heading2"].spaceAfter=7
    styles["Heading3"].fontSize=10;styles["Heading3"].leading=15
    small=ParagraphStyle("small",parent=styles["Normal"],fontSize=7.3,leading=10,spaceAfter=2)
    code_style=ParagraphStyle("code",fontName="Courier",fontSize=7,leading=10,backColor=colors.HexColor("#f0f4f7"),spaceAfter=8)
    story=[]
    story+=[Spacer(1,110),Paragraph("ORDOPLAN",styles["Heading1"]),Paragraph("Assistant d'ordonnancement multimodal et agentique",styles["Heading2"]),Spacer(1,25),Paragraph("Rapport de réalisation · version 1.0.0",styles["Normal"]),Paragraph("16 novembre 2026",styles["Normal"]),Spacer(1,25),Paragraph("Planifier. Comprendre. Valider.",styles["Heading2"]),Spacer(1,35),Paragraph("Atelier fictif · solveur vérifiable · modèles locaux · approbation humaine",styles["Normal"]),PageBreak()]
    story.append(Paragraph("Dossier de lecture",styles["Heading1"]))
    for i,name in enumerate(files,1):story.append(Paragraph(f"{i}. "+plain((ROOT/"docs"/name).read_text().splitlines()[0].lstrip("# ")),styles["Normal"]))
    story.append(Paragraph("Les sources Markdown, les résultats JSON/CSV et le code sont fournis avec ce rapport. Les chiffres viennent d'exécutions consignées ; les validations externes non effectuées sont explicitement identifiées.",styles["Normal"]))
    all_blocks=[]
    for file in files:
        story.append(PageBreak());items=blocks((ROOT/"docs"/file).read_text());all_blocks.append(items)
        for kind,value in items:
            if kind.startswith("h"):
                story.append(Paragraph(escape(plain(value)),styles[{"h1":"Heading1","h2":"Heading2","h3":"Heading3"}[kind]]))
            elif kind in ["p","bullet"]:story.append(Paragraph(escape(plain(value)),styles["Normal"]))
            elif kind=="code":story.append(Preformatted("\n".join(part for line in value.splitlines() for part in textwrap.wrap(line,94,replace_whitespace=False) or [""]),code_style))
            elif kind=="table":
                width=495;cols=max(len(r) for r in value);cell_rows=[[Paragraph(escape(plain(c)),small) for c in r]+[""]*(cols-len(r)) for r in value]
                table=Table(cell_rows,colWidths=[width/cols]*cols,repeatRows=1,hAlign="LEFT")
                table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#e1edf1")),("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,0),.6,colors.HexColor("#94aeb9")),("LINEBELOW",(0,1),(-1,-1),.2,colors.HexColor("#d5e0e4")),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]));story+=[table,Spacer(1,10)]
        images=[]
        if file=="cadrage_et_architecture.md":images=["architecture.png"]
        if file=="resultats_observes.md":images=["comparaison_solveur.png","gantt_initial.png","gantt_breakdown.png","gantt_urgent.png"]
        for name in images:
            from PIL import Image
            im=Image.open(ROOT/"reports"/name);w,h=im.size;story+=[Spacer(1,15),RLImage(str(ROOT/"reports"/name),width=495,height=495*h/w)]
    def footer(canvas,doc):
        canvas.setFont("DejaVu",7);canvas.setFillColor(colors.HexColor("#526976"));canvas.drawString(48,25,"OrdoPlan · données synthétiques · version 1.0.0");canvas.drawRightString(547,25,str(doc.page))
    SimpleDocTemplate(str(OUT/"OrdoPlan_Rapport_Final.pdf"),leftMargin=48,rightMargin=48,topMargin=45,bottomMargin=45,title="OrdoPlan — rapport de réalisation",author="Projet OrdoPlan").build(story,onFirstPage=footer,onLaterPages=footer)
    from docx import Document
    from docx.shared import Pt
    word=Document();word.add_heading("OrdoPlan",0);word.add_paragraph("Rapport de réalisation · version 1.0.0\n16 novembre 2026")
    for index,items in enumerate(all_blocks):
        word.add_page_break()
        for kind,value in items:
            if kind.startswith("h"):word.add_heading(plain(value),int(kind[1]))
            elif kind in ["p","bullet"]:word.add_paragraph(plain(value))
            elif kind=="code":
                p=word.add_paragraph();r=p.add_run(value);r.font.name="Consolas";r.font.size=Pt(8)
            else:
                table=word.add_table(rows=0,cols=max(len(r) for r in value));table.style="Light Shading Accent 1"
                for row in value:
                    cells=table.add_row().cells
                    for i,c in enumerate(row):cells[i].text=plain(c)
    word.save(OUT/"OrdoPlan_Rapport_Final.docx")
    write(ROOT/"rapport_projet.md","\n\n".join((ROOT/"docs"/name).read_text() for name in files))


def presentation():
    from pptx import Presentation
    from pptx.util import Inches,Pt
    from pptx.dml.color import RGBColor
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor
    d=read("end_to_end.json");e=read("evaluation.json")
    slides=[
        ("OrdoPlan",["Assistant d'ordonnancement multimodal et agentique","Planifier. Comprendre. Valider.","Atelier fictif · version 1.0.0"],None),
        ("Le problème d'atelier",["Des commandes, des ressources limitées et des aléas","Une panne ou une urgence impose un arbitrage rapide","Un planning calculé, vérifié et approuvé"],None),
        ("Un périmètre explicite",["2 CNC · 8 OF · familles ALU / ACIER · outil unique","Pas de commande d'automate ou de machine","La publication touche un MES de démonstration"],None),
        ("Séparer les responsabilités",["Le solveur décide des séquences et des dates","Le modèle lit ; le contrôleur vérifie","Le chef d'atelier approuve le contenu exact"],"architecture.png"),
        ("Des données reproductibles",["40 PDF synthétiques · deux familles d'équipements","50 instances + fil rouge · exports CSV/Excel et photos","1 000 triplets · séparation par document · 150 scénarios"],None),
        ("Le modèle de contraintes",["Éligibilités, réglages et NoOverlap machine","Outillage et opérateur uniques, matière et indisponibilités","Opérations engagées gelées ; aucune correction silencieuse"],None),
        ("Trois objectifs, dans cet ordre",["1. Minimiser le retard pondéré","2. Minimiser les déplacements et changements de machine","3. Minimiser la date de fin ; optimal seulement si prouvé"],None),
        ("RAG et preuves",["Filtrage atelier/rôle avant recherche et à l'ouverture","Texte + vecteurs + CLIP → RRF → reranking","Réponse extractive sourcée ; écarts chiffrés par le code"],None),
        ("Photographie et incertitude",["OCR local + VLM à poids ouverts","Un arrêt observé ne donne pas une durée de panne","Lecture incomplète ou désaccord → validation humaine"],None),
        ("Une adaptation réellement exécutée",["Cross-encoder multilingue ; deux couches et tête adaptées","600 triplets d'entraînement, 200 validation, 200 test","Scores avant/après identiques : aucun gain démontré"],None),
        ("Planning initial",[d['initial']['answer'],"Toutes les contraintes sont revérifiées indépendamment"],"gantt_initial.png"),
        ("Panne confirmée",[d['breakdown']['answer'],"La frontière d'arrêt vient du planning réellement calculé"],"gantt_breakdown.png"),
        ("Urgence et arbitrage",[d['urgent']['answer'],"Les retards sont produits par le solveur, pas par le modèle"],"gantt_urgent.png"),
        ("MCP et accord humain",["Trois outils : commandes, état machine, publication","Interruption LangGraph avant l'action sensible","Hash + utilisateur + atelier + révision ; expiration et idempotence"],None),
        ("Sécurité vérifiée",["Accès inter-ateliers refusé, y compris pour les PDF/images","Notes et OCR hostiles sans effet sur les contraintes","Jeton absent, modifié ou expiré : publication bloquée"],None),
        ("Résultats observés",[f"{e['passed']}/150 scénarios de composants réussis","30 plannings valides, 0 contrainte violée ; CP-SAT ≤ FIFO/EDD",f"25 replanifications ; p95 solveur {e['replanning']['p95_seconds']:.3f} s sur ces cas"],"comparaison_solveur.png"),
        ("Limites à présenter",["Données synthétiques et requêtes de recherche faciles","Petit VLM CPU insuffisant ; pas de benchmark GPU ni d'entretien terrain","Mono-opération, pas de suspension/reprise ; Telegram réel à configurer"],None),
        ("Livraison et suite",["Code, données, tests, Docker, guides et modèles locaux","Rapports calculés et support de démonstration","Avant usage réel : qualifier les règles et les sources avec l'atelier"],None),
    ]
    prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
    pdf=canvas.Canvas(str(OUT/"OrdoPlan_Soutenance.pdf"),pagesize=(960,540))
    for i,(title,lines,image) in enumerate(slides,1):
        slide=prs.slides.add_slide(prs.slide_layouts[6]);background=slide.background.fill;background.solid();background.fore_color.rgb=RGBColor.from_string("F5F8FA")
        box=slide.shapes.add_textbox(Inches(.55),Inches(.35),Inches(12.2),Inches(.8));tf=box.text_frame;tf.text=title
        tf.paragraphs[0].font.size=Pt(31);tf.paragraphs[0].font.bold=True;tf.paragraphs[0].font.color.rgb=RGBColor.from_string("163E4D")
        box=slide.shapes.add_textbox(Inches(.65),Inches(1.45),Inches(12),Inches(2.1 if image else 4.5));tf=box.text_frame;tf.word_wrap=True
        for j,line in enumerate(lines):
            p=tf.paragraphs[0] if j==0 else tf.add_paragraph();p.text=line;p.font.size=Pt(18 if image else 23);p.space_after=Pt(16);p.font.color.rgb=RGBColor.from_string("294757")
        if image:slide.shapes.add_picture(str(ROOT/"reports"/image),Inches(1),Inches(3.7),width=Inches(11.3),height=Inches(3.0))
        footer=slide.shapes.add_textbox(Inches(.6),Inches(7.0),Inches(12),Inches(.25));footer.text_frame.text=f"OrdoPlan · atelier fictif · {i:02d}/{len(slides):02d}"
        footer.text_frame.paragraphs[0].font.size=Pt(10)
        slide.notes_slide.notes_text_frame.text="Présenter les éléments de cette diapositive à partir des preuves dans reports/. Ne pas annoncer de validation industrielle, de gain neuronal ou de connexion Telegram non effectués. Voir docs/demonstration.md pour le déroulé et les questions."
        pdf.setFillColor(HexColor("#f5f8fa"));pdf.rect(0,0,960,540,fill=1,stroke=0);pdf.setFillColor(HexColor("#163e4d"));pdf.setFont("DejaVuBold",25);pdf.drawString(40,490,title)
        pdf.setFont("DejaVu",15 if image else 20);y=435
        for line in lines:
            for part in textwrap.wrap(line,96 if image else 74):pdf.drawString(46,y,part);y-=23 if image else 30
            y-=8
        if image:pdf.drawImage(str(ROOT/"reports"/image),65,48,width=830,height=230,preserveAspectRatio=True,anchor="c",mask="auto")
        pdf.setFont("DejaVu",9);pdf.drawString(42,20,f"OrdoPlan · atelier fictif · {i:02d}/{len(slides):02d}");pdf.showPage()
    prs.save(OUT/"OrdoPlan_Soutenance.pptx");pdf.save()
    write(ROOT/"docs/soutenance_notes.md","# Notes de soutenance\n\n"+"\n\n".join(f"## {i}. {title}\n\n"+"\n".join('- '+v for v in lines) for i,(title,lines,image) in enumerate(slides,1)))


def main():
    os.environ.setdefault("MPLCONFIGDIR",str(ROOT/".runtime/matplotlib"))
    OUT.mkdir(parents=True,exist_ok=True)
    generate_narratives();figures();documents();presentation()
    print("Rapport PDF/DOCX et 18 diapositives PPTX/PDF générés depuis les mesures réelles.")


if __name__=="__main__":main()
