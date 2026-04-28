FROM python:3.11-slim AS builder
WORKDIR /build
COPY shared-mcp-lib/ shared-mcp-lib/
COPY docusign-mcp-app/ docusign-mcp-app/
RUN pip install --no-cache-dir --prefix=/opt/venv ./shared-mcp-lib ./docusign-mcp-app

FROM python:3.11-slim AS runtime
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH="/opt/venv/lib/python3.11/site-packages"
ENV PYTHONUNBUFFERED=1
EXPOSE 3005
CMD ["python", "-m", "docusign_mcp"]
