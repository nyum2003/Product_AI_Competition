FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY engine.py server.py ./
COPY static ./static
ENV HOST=0.0.0.0 PORT=8000 CASEFLOW_DB=/data/caseflow.sqlite3
RUN useradd --create-home caseflow && mkdir /data && chown caseflow /data
USER caseflow
VOLUME ["/data"]
EXPOSE 8000
CMD ["python", "server.py"]
