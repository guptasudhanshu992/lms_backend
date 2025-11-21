# Procfile for Fly.io buildpack deployment
# This tells Fly.io how to run your app without Docker

# Run database migrations then start server
release: alembic upgrade head
web: uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
