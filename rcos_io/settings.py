import os


def env_get(env_var: str) -> str:
    """Gets the value of an environment variable or throws a `KeyError` if it is not set."""
    val = os.environ.get(env_var)
    if not val:
        raise KeyError(f"Env variable '{env_var}' is not set!")
    return val


GQL_API_URL = env_get("GQL_API_URL")
HASURA_ADMIN_SECRET = env_get("HASURA_ADMIN_SECRET")
DISCORD_REDIRECT_URL = env_get("DISCORD_REDIRECT_URL")
DISCORD_CLIENT_ID = env_get("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = env_get("DISCORD_CLIENT_SECRET")
DISCORD_BOT_TOKEN = env_get("DISCORD_BOT_TOKEN")
DISCORD_SERVER_ID = env_get("DISCORD_SERVER_ID")
ENV = env_get("ENV")
SECRET_KEY = env_get("SECRET_KEY")
