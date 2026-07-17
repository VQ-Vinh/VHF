FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY services/prana_api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 prana
COPY --chown=prana:prana services/prana_api ./services/prana_api
USER prana
CMD ["sh", "-c", "uvicorn services.prana_api.main:app --host 0.0.0.0 --port ${PORT}"]
