FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY sf_crm_mcp/ sf_crm_mcp/

RUN pip install --no-cache-dir -e .

EXPOSE 3000

CMD ["python", "-m", "sf_crm_mcp"]
