FROM python:3.11-slim AS builder
WORKDIR /app
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml .
COPY sap_s4hana_mcp/ sap_s4hana_mcp/
RUN pip install --no-cache-dir .

FROM python:3.11-slim AS runtime
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
EXPOSE 3002
CMD ["python", "-m", "sap_s4hana_mcp"]
