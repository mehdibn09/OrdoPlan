FROM python:3.12.14-slim-bookworm
ARG RUN_SMOKE_TEST=0
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 LANGCHAIN_TRACING_V2=false ANONYMIZED_TELEMETRY=false
WORKDIR /app
COPY --chown=10001:10001 . .
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-fra tesseract-ocr-eng fonts-dejavu-core libgomp1 && rm -rf /var/lib/apt/lists/* && pip install pip==26.3 setuptools==84.1.0 && pip install -r requirements.txt && useradd --create-home --uid 10001 ordoplan && mkdir -p /app/.runtime && chown -R ordoplan:ordoplan /app/.runtime /app/reports && if [ "$RUN_SMOKE_TEST" = "1" ]; then pip install pytest==9.0.3 pytest-asyncio==1.3.0 && su -s /bin/sh ordoplan -c 'python -m scripts.build_smoke'; fi
USER ordoplan
EXPOSE 8000 8101 8501
CMD ["python","-m","uvicorn","src.api.main:app","--host","0.0.0.0","--port","8000","--no-access-log"]
