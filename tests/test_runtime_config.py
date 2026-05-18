from pathlib import Path

from config.runtime import database_url_for_container


def test_database_url_for_container_rewrites_localhost_to_db():
    url = "postgres://factflow:factflow@localhost:5432/factflow"

    assert database_url_for_container(url) == (
        "postgres://factflow:factflow@db:5432/factflow"
    )


def test_database_url_for_container_keeps_remote_host_for_supabase():
    url = (
        "postgresql://postgres.abc:secret@aws-0-eu-central-1.pooler.supabase.com:"
        "5432/postgres?sslmode=require"
    )

    assert database_url_for_container(url) == url


def test_entrypoint_normalizes_database_url_for_container():
    entrypoint = Path("entrypoint.sh").read_text()

    assert "database_url_for_container" in entrypoint


def test_docker_compose_does_not_force_database_url_override():
    compose_text = Path("docker-compose.yml").read_text()

    assert (
        "DATABASE_URL=postgres://factflow:factflow@db:5432/factflow"
        not in compose_text
    )
