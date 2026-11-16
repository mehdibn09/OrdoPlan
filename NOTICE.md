# Licences et attribution

Le code original OrdoPlan de cette livraison est distribué sous GNU AGPL v3 ou ultérieure, voir `LICENSE`. Les données, textes et images synthétiques produits pour le corpus sont proposés sous CC0-1.0. Le code du camarade de classe et les documents de sujet ne sont pas redistribués dans le dépôt.

Les dépendances conservent leurs licences propres. Les métadonnées observées sont dans `reports/dependencies_licenses.json` : OR-Tools Apache-2.0, SDK MCP MIT, LangChain/LangGraph MIT, Qdrant Apache-2.0, FastAPI MIT, Streamlit Apache-2.0, PyMuPDF AGPL/commercial, notamment. Les textes amont restent applicables ; ce relevé n'est pas un audit juridique.

Les modèles ouverts sont identifiés par dépôt, révision et licence annoncée dans `models/models.lock.json`. Le pack conserve leurs fichiers de configuration et notices. Le reranker adapté dérive de `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` et conserve l'attribution de sa base. Les paramètres d'adaptation, le hash du dataset et les résultats observés sont livrés. Aucun score de l'archive d'exemple n'est réutilisé.
