#!/bin/sh
set -e

echo "==> Applico le migrazioni del database..."
python manage.py migrate --noinput

echo "==> Raccolgo i file statici..."
python manage.py collectstatic --noinput

echo "==> Avvio gunicorn..."
# Un solo worker: l'app avvia un BackgroundScheduler in-process (apps.py) per
# aggiornare i calendari iCal esterni ogni 15 min. Con più worker gunicorn
# partirebbero più scheduler duplicati. --threads gestisce comunque le
# richieste concorrenti all'interno dello stesso worker.
exec gunicorn django_project.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --threads 4 \
    --timeout 60
