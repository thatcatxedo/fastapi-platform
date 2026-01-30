FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all Python modules
COPY main.py config.py database.py models.py auth.py validation.py utils.py lifespan.py ./
COPY deployment.py cleanup.py seed_templates.py mongo_users.py migrate_mongo_users.py migrate_admin_role.py ./
COPY routers/ ./routers/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
