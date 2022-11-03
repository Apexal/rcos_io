import os
from dotenv import load_dotenv

load_dotenv()


def env_get(env_var: str) -> str:
    """Returns the value of an environment variable or throws a `KeyError` if it is not set."""
    val = os.environ.get(env_var)
    # fetches value from .env file in root directory with "env_var" as the key
    if not val:
        raise KeyError(f"Env variable '{env_var}' is not set!")
        # occurs if key doesn't exist or .env file doesn't exist
    return val


GQL_API_URL = env_get("GQL_API_URL")
"""URL to RCOS Hasura API for GraphQL requests"""

HASURA_ADMIN_SECRET = env_get("HASURA_ADMIN_SECRET")
"""Admin password for full access to RCOS Hasura"""

HASURA_PROJECT_URL = env_get("HASURA_PROJECT_URL")
"""URL to the Hasura console for the database"""

DISCORD_REDIRECT_URL = env_get("DISCORD_REDIRECT_URL")
"""URL to that Discord redirects to at the end of its OAuth2 flow"""
# url for discord oauth

DISCORD_CLIENT_ID = env_get("DISCORD_CLIENT_ID")
"""
Client ID for Discord application

See https://discord.com/developers/docs/resources/user#user-object-example-user
"""

DISCORD_CLIENT_SECRET = env_get("DISCORD_CLIENT_SECRET")
"""Secret token of the Discord application"""

DISCORD_BOT_TOKEN = env_get("DISCORD_BOT_TOKEN")
"""Unique token that identifies the Discord application bot"""

DISCORD_SERVER_ID = env_get("DISCORD_SERVER_ID")
"""
The ID of the RCOS Discord server

See https://discord.com/developers/docs/resources/guild#guild-object-guild-structure
"""

ENV = env_get("ENV")
"""The environment the server is running in. Expected to be either `'development'` or `'production'`"""

SECRET_KEY = env_get("SECRET_KEY")
"""Secret random value used by Flask to secure cookies to store session data"""

# discord id reference: https://discord.com/developers/docs/reference#snowflakes
# discord bot platform: https://discord.com/developers/applications

GITHUB_APP_CLIENT_ID = env_get("GITHUB_APP_CLIENT_ID")
"""Client ID for the GitHub App"""

GITHUB_APP_CLIENT_SECRET = env_get("GITHUB_APP_CLIENT_SECRET")
"""Client secret for the GitHub App used to authorize requests"""

GITHUB_APP_REDIRECT_URL = env_get("GITHUB_APP_REDIRECT_URL")
"""URL GitHub redirects to after the OAuth2 flow"""

# github app docs: https://docs.github.com/en/developers/apps/getting-started-with-apps/about-apps
