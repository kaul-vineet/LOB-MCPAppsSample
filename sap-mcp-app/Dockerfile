FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY sap_s4hana_mcp/ sap_s4hana_mcp/

RUN pip install --no-cache-dir -e .

EXPOSE 3002

CMD ["python", "-m", "sap_s4hana_mcp"]
