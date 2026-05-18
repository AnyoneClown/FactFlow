"""Runtime helpers for container-specific configuration adjustments."""

from urllib.parse import urlsplit, urlunsplit


def database_url_for_container(database_url: str) -> str:
    """Rewrite local Postgres hosts to the Docker service hostname."""

    parts = urlsplit(database_url)
    if parts.hostname not in {"localhost", "127.0.0.1"}:
        return database_url

    auth = ""
    if parts.username is not None:
        auth = parts.username
        if parts.password is not None:
            auth = f"{auth}:{parts.password}"
        auth = f"{auth}@"

    host = "db"
    if parts.port is not None:
        host = f"{host}:{parts.port}"

    netloc = f"{auth}{host}"
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
