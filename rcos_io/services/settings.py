"""
This module reads the environment variables needed to run the site
and stores them as constants for easy use in other modules.

If any of these are missing a value (they are not set in the environment),
`env_get` throws a `KeyError` and the program will crash on startup.
Every environment variable constant should have a docstring
describing what it is used for. When developing locally,
`load_dotenv()` will look for a `.env` file in the top-level folder
with these environment variables set.

When in production, there's no `.env` file and environment variables
are just set in the environment.

See https://12factor.net/config
"""

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

HASURA_CONSOLE_URL = env_get("HASURA_CONSOLE_URL")
"""URL to the Hasura console for the database"""

RAILWAY_PROJECT_URL = env_get("RAILWAY_PROJECT_URL")
"""URL to Railway project dashboard for managing infrastructure"""

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
"""
The environment the server is running in.
Expected to be either `'development'` or `'production'`
"""

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

REDISHOST = env_get("REDISHOST")
"""Address for the Redis cache"""

REDISPORT = env_get("REDISPORT")
"""Port for the Redis cache"""

REDISUSER = env_get("REDISUSER")
"""Username for the RCOS I/O user in Redis"""

REDISPASSWORD = env_get("REDISPASSWORD")
"""Password for the RCOS I/O user in Redis"""

MAILJET_API_KEY = env_get("MAILJET_API_KEY")

MAILJET_API_SECRET = env_get("MAILJET_API_SECRET")

# Database

PGDATABASE = env_get("PGDATABASE")

PGHOST = env_get("PGHOST")

PGPASSWORD = env_get("PGPASSWORD")

PGPORT = env_get("PGPORT")

PGUSER = env_get("PGUSER")
