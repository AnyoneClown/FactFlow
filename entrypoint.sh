#!/bin/sh
set -eu

if [ -n "${DATABASE_URL:-}" ]; then
  export DATABASE_URL="$(python -c "import os; from config.runtime import database_url_for_container; print(database_url_for_container(os.environ['DATABASE_URL']))")"
fi

python manage.py migrate
python manage.py bootstrap_local

exec python manage.py runserver 0.0.0.0:8000
