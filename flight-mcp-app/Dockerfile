FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
COPY flight_mcp ./flight_mcp
RUN pip install --no-cache-dir .
EXPOSE 3004
CMD ["python", "-m", "flight_mcp"]
