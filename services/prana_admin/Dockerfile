FROM python:3.12-slim@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea

ARG VCS_REF=unknown
ARG BUILD_URL=unknown
ARG BUILD_RUN_ID=unknown
LABEL org.opencontainers.image.source="https://github.com/VQ-Vinh/VHF" \
      org.opencontainers.image.revision="$VCS_REF" \
      org.opencontainers.image.version="$VCS_REF" \
      org.opencontainers.image.url="$BUILD_URL" \
      org.opencontainers.image.title="prana-admin" \
      io.github.actions.run-id="$BUILD_RUN_ID" \
      io.prana.service="prana-admin"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8080
WORKDIR /app
COPY services/prana_admin/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --create-home --uid 10001 prana
COPY --chown=prana:prana services/prana_admin ./services/prana_admin
USER prana
CMD ["sh", "-c", "uvicorn services.prana_admin.main:app --host 0.0.0.0 --port ${PORT}"]
