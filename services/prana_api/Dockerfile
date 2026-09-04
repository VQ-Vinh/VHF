FROM python:3.14-slim@sha256:cad9a2c871761c413caa6fdd6441c783451e740a48aaeba60ae62a8b53525ef6

ARG VCS_REF=unknown
ARG BUILD_URL=unknown
ARG BUILD_RUN_ID=unknown
LABEL org.opencontainers.image.source="https://github.com/VQ-Vinh/VHF" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.version="$VCS_REF" \
      org.opencontainers.image.url="$BUILD_URL" \
      org.opencontainers.image.title="prana-api" \
      io.github.actions.run-id="$BUILD_RUN_ID" \
      io.prana.service="prana-api"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY services/prana_api/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 prana
COPY --chown=prana:prana services/prana_api ./services/prana_api
USER prana
CMD ["sh", "-c", "uvicorn services.prana_api.main:app --host 0.0.0.0 --port ${PORT}"]
