FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY servicenow_mcp/ servicenow_mcp/

RUN pip install --no-cache-dir -e .

EXPOSE 3001

CMD ["python", "-m", "servicenow_mcp"]
