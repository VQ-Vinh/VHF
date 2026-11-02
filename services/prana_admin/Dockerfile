FROM python:3.15-slim@sha256:94d3426f1def7db4a106a232ac121bfd975393e5dfd40a619b955fae45fe7913

# Apply Debian's perl-base security fixes missing from the pinned base image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends --only-upgrade perl-base \
    && rm -rf /var/lib/apt/lists/*

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
