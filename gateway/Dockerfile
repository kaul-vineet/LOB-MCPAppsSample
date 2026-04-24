# Build context must be the project root:
#   docker build -f gateway/Dockerfile .
# docker-compose uses: build: { context: ., dockerfile: gateway/Dockerfile }

FROM python:3.11-slim AS builder
WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy shared lib + all 10 LOB apps + gateway (context = project root)
COPY shared-mcp-lib/ shared-mcp-lib/
COPY sf-mcp-app/ sf-mcp-app/
COPY snow-mcp-app/ snow-mcp-app/
COPY sap-mcp-app/ sap-mcp-app/
COPY hubspot-mcp-app/ hubspot-mcp-app/
COPY flight-mcp-app/ flight-mcp-app/
COPY docusign-mcp-app/ docusign-mcp-app/
COPY saphr-mcp-app/ saphr-mcp-app/
COPY workday-mcp-app/ workday-mcp-app/
COPY coupa-mcp-app/ coupa-mcp-app/
COPY jira-mcp-app/ jira-mcp-app/
COPY gateway/ gateway/

RUN pip install --no-cache-dir \
    ./shared-mcp-lib \
    ./sf-mcp-app \
    ./snow-mcp-app \
    ./sap-mcp-app \
    ./hubspot-mcp-app \
    ./flight-mcp-app \
    ./docusign-mcp-app \
    ./saphr-mcp-app \
    ./workday-mcp-app \
    ./coupa-mcp-app \
    ./jira-mcp-app \
    ./gateway

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "-m", "gateway"]
