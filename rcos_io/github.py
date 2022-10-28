import requests
from typing import TypedDict
from rcos_io.settings import (
    GITHUB_APP_CLIENT_ID,
    GITHUB_APP_CLIENT_SECRET,
    GITHUB_APP_REDIRECT_URL
)

GITHUB_API_ENDPOINT = "https://api.github.com"
GITHUB_AUTH_URL = f"https://github.com/login/oauth/authorize?client_id={GITHUB_APP_CLIENT_ID}&redirect_uri={GITHUB_APP_REDIRECT_URL}"

class GitHubTokens(TypedDict):
    access_token: str
    scope: str
    token_type: int

def get_tokens(code: str) -> GitHubTokens:
    """
    Given an authorization code, request an access token for a GitHub user. Returns the token data. Throws an error if invalid request.

    See https://docs.github.com/en/developers/apps/building-oauth-apps/authorizing-oauth-apps#2-users-are-redirected-back-to-your-site-by-github
    """
    response = requests.post(
        f"https://github.com//login/oauth/access_token",
        data={
            "client_id": GITHUB_APP_CLIENT_ID,
            "client_secret": GITHUB_APP_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_APP_REDIRECT_URL,
        },
        headers={
            "Accept": "application/json"
        }
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    tokens = response.json()
    return tokens

class GitHubUser(TypedDict):
    id: str
    login: str
    avatar_url: str # link to github profile page

def get_user_info(access_token: str) -> GitHubUser:
    """
    Given an access token, get a GitHub user's info including id, username (login), avatar_url, etc. Throws an error on failed request.

    See https://docs.github.com/en/rest/users/users#get-the-authenticated-user
    """
    response = requests.get(
        f"{GITHUB_API_ENDPOINT}/user",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/vnd.github+json",
        },
    )
    response.raise_for_status()
    # https://requests.readthedocs.io/en/latest/user/quickstart/#response-status-codes
    # throws HTTPError for 4XX or 5XX
    user = response.json()
    return user