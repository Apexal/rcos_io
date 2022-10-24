from typing import Any, Dict
import requests
import os

DISCORD_VERSION_NUMBER = "10"
DISCORD_API_ENDPOINT = f"https://discord.com/api/v{DISCORD_VERSION_NUMBER}"
DISCORD_REDIRECT_URL = os.environ.get("DISCORD_REDIRECT_URL")
DISCORD_CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET")
DISCORD_BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
DISCORD_SERVER_ID = os.environ.get("DISCORD_SERVER_ID")

# See https://discord.com/developers/docs/topics/oauth2#authorization-code-grant
DISCORD_AUTH_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URL}&response_type=code&scope=identify%20guilds.join&prompt=none"

HEADERS = {
    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
}


def get_tokens(code: str) -> Dict[str, Any]:
    """
    Given an authorization code, request the access and refresh tokens for a Discord user. Returns the tokens. Throws an error if invalid request.

    See https://discord.com/developers/docs/topics/oauth2#authorization-code-grant-access-token-exchange-example
    """
    response = requests.post(
        f"{DISCORD_API_ENDPOINT}/oauth2/token",
        data={
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URL,
            "scope": "identity guilds.join",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    response.raise_for_status()
    tokens = response.json()
    return tokens


def get_user_info(access_token: str) -> Dict[str, Any]:
    """
    Given an access token, get a Discord user's info including id, username, discriminator, avatar url, etc. Throws an error if failed request.

    See https://discord.com/developers/docs/topics/oauth2#authorization-code-grant-access-token-exchange-example
    """
    response = requests.get(
        f"{DISCORD_API_ENDPOINT}/users/@me",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    response.raise_for_status()
    user = response.json()
    return user


def add_user_to_server(access_token: str, user_id: str, nickname: str | None = None):
    """
    Given a Discord user's id, add them to the RCOS server with the given nickname. Throws an error if failed request.

    See https://discord.com/developers/docs/resources/guild#add-guild-member
    """
    data = {
        "access_token": access_token,
    }
    if nickname:
        data["nick"] = nickname
    response = requests.put(
        f"{DISCORD_API_ENDPOINT}/guilds/{DISCORD_SERVER_ID}/members/{user_id}",
        json=data,
        headers=HEADERS,
    )
    response.raise_for_status()
    return response
