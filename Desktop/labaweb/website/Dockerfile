FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN python -m pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8002
EXPOSE 5432

CMD ["uvicorn", "website:app", "--host", "0.0.0.0", "--port", "8002"]