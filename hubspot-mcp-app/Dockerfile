FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY hubspot_mcp/ hubspot_mcp/

RUN pip install --no-cache-dir -e .

EXPOSE 3003

CMD ["python", "-m", "hubspot_mcp"]
