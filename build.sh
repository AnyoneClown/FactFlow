#!/usr/bin/env bash
set -o errexit

pip install poetry
poetry config virtualenvs.create false
poetry install --only main --no-interaction --no-ansi
poetry run python manage.py collectstatic --noinput
