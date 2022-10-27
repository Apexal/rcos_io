from typing import Any, Dict, Optional, TypedDict, Union
from typing_extensions import NotRequired
import requests
from rcos_io.settings import (
    DISCORD_BOT_TOKEN,
    DISCORD_CLIENT_ID,
    DISCORD_CLIENT_SECRET,
    DISCORD_REDIRECT_URL,
    DISCORD_SERVER_ID,
)

DISCORD_VERSION_NUMBER = "10"
DISCORD_API_ENDPOINT = f"https://discord.com/api/v{DISCORD_VERSION_NUMBER}"


# See https://discord.com/developers/docs/topics/oauth2#authorization-code-grant
DISCORD_AUTH_URL = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={DISCORD_REDIRECT_URL}&response_type=code&scope=identify%20guilds.join&prompt=none"

HEADERS = {
    "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
}

class DiscordTokens(TypedDict):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    scope: str

def get_tokens(code: str) -> DiscordTokens:
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

class DiscordUser(TypedDict):
    id: str
    username: str
    discriminator: str
    avatar: NotRequired[str]
    banner: NotRequired[str]
    accent_color: NotRequired[str]

def get_user_info(access_token: str) -> DiscordUser:
    """
    Given an access token, get a Discord user's info including id, username, discriminator, avatar url, etc. Throws an error on failed request.

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


def add_user_to_server(access_token: str, user_id: str):
    """
    Given a Discord user's id, add them to the RCOS server with the given nickname. Throws an error on failed request.

    See https://discord.com/developers/docs/resources/guild#add-guild-member
    """
    data = {
        "access_token": access_token,
    }
    response = requests.put(
        f"{DISCORD_API_ENDPOINT}/guilds/{DISCORD_SERVER_ID}/members/{user_id}",
        json=data,
        headers=HEADERS,
    )
    response.raise_for_status()
    return response

def get_user(discord_user_id: str) -> Union[DiscordUser, None]:
    response = requests.get(
        f"{DISCORD_API_ENDPOINT}/users/{discord_user_id}",
        headers=HEADERS,
    )
    response.raise_for_status()
    user = response.json()
    return user

def add_role_to_member(user_id: str, role_id: str):
    """Add a role (identified by its id) to a server member. Throws an error on failed request."""
    response = requests.put(
        f"{DISCORD_API_ENDPOINT}/guilds/{DISCORD_SERVER_ID}/members/{user_id}/roles/{role_id}",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response


def kick_user_from_server(user_id: str):
    """Given a Discord user's id, kick them from the RCOS server. Throws an error on failed request."""
    response = requests.delete(
        f"{DISCORD_API_ENDPOINT}/guilds/{DISCORD_SERVER_ID}/members/{user_id}",
        headers=HEADERS,
    )
    response.raise_for_status()
    return response


def set_member_nickname(user_id: str, nickname: str):
    """Given a Discord user's id, set their nickname on the server. Throws an error on failed request."""
    response = requests.patch(
        f"{DISCORD_API_ENDPOINT}/guilds/{DISCORD_SERVER_ID}/members/{user_id}",
        json={"nick": nickname},
        headers=HEADERS,
    )
    response.raise_for_status()
    return response


def generate_nickname(user: Dict[str, Any]) -> str | None:
    name = ""
    if user["first_name"] and user["last_name"]:
        name = f"{user['first_name']} {user['last_name'][0]}"
    elif user["first_name"]:
        name = user["first_name"]
    elif user["rcs_id"]:
        return user["rcs_id"]

    nickname = name
    if user["graduation_year"]:
        nickname += f" '{str(user['graduation_year'])[2:4]}"

    if user["rcs_id"]:
        nickname += f" ({user['rcs_id']})"

    return nickname
