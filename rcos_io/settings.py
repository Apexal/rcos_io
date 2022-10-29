import os


def env_get(env_var: str) -> str:
    """Gets the value of an environment variable or throws a `KeyError` if it is not set."""
    val = os.environ.get(env_var)
    # fetches value from .env file in root directory with "env_var" as the key
    if not val:
        raise KeyError(f"Env variable '{env_var}' is not set!")
        # occurs if key doesn't exist or .env file doesn't exist
    return val


GQL_API_URL = env_get("GQL_API_URL")
# url for querying rcos database with graphql

HASURA_ADMIN_SECRET = env_get("HASURA_ADMIN_SECRET")
# admin password for database access

DISCORD_REDIRECT_URL = env_get("DISCORD_REDIRECT_URL")
# url for discord oauth

DISCORD_CLIENT_ID = env_get("DISCORD_CLIENT_ID")
# discord bot id
# example: https://discord.com/developers/docs/resources/user#user-object-example-user

DISCORD_CLIENT_SECRET = env_get("DISCORD_CLIENT_SECRET")
# discord bot password

DISCORD_BOT_TOKEN = env_get("DISCORD_BOT_TOKEN")
# discord bot token

DISCORD_SERVER_ID = env_get("DISCORD_SERVER_ID")
# discord server id
# example: https://discord.com/developers/docs/resources/guild#guild-object-guild-structure

ENV = env_get("ENV")
# development/production

SECRET_KEY = env_get("SECRET_KEY")
# used for securing flask server

# discord id reference: https://discord.com/developers/docs/reference#snowflakes
# discord bot platform: https://discord.com/developers/applications

GITHUB_APP_CLIENT_ID = env_get("GITHUB_APP_CLIENT_ID")
# github app id

GITHUB_APP_CLIENT_SECRET = env_get("GITHUB_APP_CLIENT_SECRET")
# github app password

GITHUB_APP_REDIRECT_URL = env_get("GITHUB_APP_REDIRECT_URL")
# github app oauth link

# github app docs: https://docs.github.com/en/developers/apps/getting-started-with-apps/about-apps
