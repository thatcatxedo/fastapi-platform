FROM python:3.11-slim

WORKDIR /app

# Install whitelisted packages
# Pin python-fasthtml to latest known working version
RUN pip install --no-cache-dir \
    fastapi==0.109.0 \
    uvicorn[standard]==0.27.0 \
    pydantic==2.5.3 \
    python-fasthtml==0.12.39 \
    pymongo==4.6.1 \
    jinja2==3.1.3 \
    httpx==0.26.0 \
    slack-sdk==3.27.1 \
    google-auth==2.27.0 \
    google-api-python-client==2.108.0

# Copy entrypoint script
COPY entrypoint.py .
COPY runner.py .

EXPOSE 8000

CMD ["python", "entrypoint.py"]
