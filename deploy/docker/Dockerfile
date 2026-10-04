# sgit vaults API — API-only image (no UI overlay), one image for Docker, Lambda, Fargate, Cloud Run.
#
# Until phase-1 step 1.3 lands the code in this repo, the image serves the vault API from the
# published origin package (sgraph-ai-app-send, pinned) — the same app that runs today on
# dev.send.sgraph.ai, booted standalone. serve.py switches to sgit_vaults when it is importable.
# Nothing about the API's behaviour changes here; only where it is built and deployed from.

FROM python:3.12-slim

# AWS Lambda Web Adapter: makes this same image runnable as a Lambda container-image function
# (translates Function-URL events <-> HTTP on :8080). Inert everywhere else.
COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:0.9.1 /lambda-adapter /opt/extensions/lambda-adapter
ENV AWS_LWA_READINESS_CHECK_PATH=/api/info/health

ARG ORIGIN_PACKAGE_VERSION=0.33.69
WORKDIR /app
COPY deploy/docker/requirements.txt ./requirements.txt
RUN sed -i "s/^sgraph-ai-app-send.*/sgraph-ai-app-send==${ORIGIN_PACKAGE_VERSION}/" requirements.txt \
 && pip install --no-cache-dir -r requirements.txt

# this repo's package (the destination of the move) — a no-op for the API until step 1.3
COPY pyproject.toml README.md ./
COPY sgit_ai_api/ ./sgit_ai_api/
RUN pip install --no-cache-dir -e .

COPY deploy/docker/serve.py ./serve.py

RUN mkdir -p /data && useradd --create-home --uid 10001 app && chown -R app:app /data /app
EXPOSE 8080

ENV SEND__STORAGE_MODE=disk
ENV SEND__DISK_PATH=/data
ENV SEND__STORAGE_BASE=
ENV SEND__STORAGE_VERSION=
ENV SEND__DEPLOYMENT_ID=

LABEL org.opencontainers.image.source="https://github.com/SGit-AI/SGit-AI__API" \
      org.opencontainers.image.title="sgit-vaults-api" \
      org.opencontainers.image.description="sgit vaults API — zero-knowledge encrypted vault server (API only)" \
      org.opencontainers.image.licenses="Apache-2.0"

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8080\")}/api/info/health')" || exit 1

USER app
CMD ["python", "serve.py"]
