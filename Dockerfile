FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi.py \
    FLASK_CONFIG=prod

WORKDIR /app

# 1) dependances d'abord : cette couche reste en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) puis le code
COPY . .

# utilisateur non-root
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status == 200 else 1)"

# applique les migrations puis lance Gunicorn (4 workers)
CMD ["sh", "-c", "flask db upgrade && exec gunicorn -w 4 -b 0.0.0.0:8000 --access-logfile - wsgi:app"]