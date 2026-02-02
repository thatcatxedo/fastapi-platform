FROM python:3.11-slim

WORKDIR /app

# Install whitelisted packages
# python-fasthtml 0.12.x requires uvicorn>=0.30
# fasthtml-auth dependencies: monsterui, fastlite, bcrypt
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    'uvicorn[standard]>=0.30' \
    pydantic==2.5.3 \
    python-fasthtml==0.12.39 \
    fasthtml-auth==0.2.0 \
    monsterui>=1.0.20 \
    fastlite>=0.2.0 \
    bcrypt>=4.0.0 \
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
