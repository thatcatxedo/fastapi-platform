FROM python:3.11-slim

WORKDIR /app

# Install whitelisted packages
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    pydantic==2.5.3 \
    python-fasthtml

# Copy entrypoint script
COPY entrypoint.py .
COPY runner.py .

EXPOSE 8000

CMD ["python", "entrypoint.py"]
