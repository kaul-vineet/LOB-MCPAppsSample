FROM python:3.11-slim AS builder
WORKDIR /build
COPY shared-mcp-lib/ shared-mcp-lib/
COPY sap-mcp-app/ sap-mcp-app/
RUN pip install --no-cache-dir --prefix=/opt/venv ./shared-mcp-lib ./sap-mcp-app

FROM python:3.11-slim AS runtime
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH="/opt/venv/lib/python3.11/site-packages"
ENV PYTHONUNBUFFERED=1
EXPOSE 3002
CMD ["python", "-m", "sap_s4hana_mcp"]
