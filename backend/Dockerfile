FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY etl_loader.py .
COPY app ./app
COPY olist_bi_schema.sql .
COPY knowledge_base.txt .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
