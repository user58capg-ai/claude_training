"""GitHub MCP server.

Exposes GitHub REST API operations as MCP tools over stdio.
Authentication: set the GITHUB_TOKEN environment variable to a GitHub
Personal Access Token (classic or fine-grained) with `repo` scope.
"""

import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load GITHUB_TOKEN from the .env file next to this script, regardless of
# the working directory the MCP client launches the server from.
load_dotenv(Path(__file__).parent / ".env")

mcp = FastMCP("github")

GITHUB_API = "https://api.github.com"


def _headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "github-mcp-server",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _request(method: str, path: str, **kwargs: Any) -> Any:
    """Call the GitHub API and return parsed JSON, raising on errors."""
    with httpx.Client(base_url=GITHUB_API, headers=_headers(), timeout=30) as client:
        response = client.request(method, path, **kwargs)
        if response.status_code == 401:
            raise RuntimeError(
                "GitHub authentication failed. Set the GITHUB_TOKEN environment "
                "variable to a valid Personal Access Token."
            )
        response.raise_for_status()
        if response.status_code == 204:
            return {"status": "success"}
        return response.json()


@mcp.tool()
def get_authenticated_user() -> dict:
    """Get the profile of the user the GITHUB_TOKEN belongs to. Useful to verify the connection works."""
    user = _request("GET", "/user")
    return {
        "login": user["login"],
        "name": user.get("name"),
        "public_repos": user.get("public_repos"),
        "private_repos": user.get("total_private_repos"),
        "html_url": user["html_url"],
    }


@mcp.tool()
def list_repos(per_page: int = 30, sort: str = "updated") -> list[dict]:
    """List repositories for the authenticated user.

    Args:
        per_page: Number of repos to return (max 100).
        sort: Sort order - one of "created", "updated", "pushed", "full_name".
    """
    repos = _request("GET", "/user/repos", params={"per_page": per_page, "sort": sort})
    return [
        {
            "full_name": r["full_name"],
            "description": r.get("description"),
            "private": r["private"],
            "default_branch": r["default_branch"],
            "language": r.get("language"),
            "stars": r["stargazers_count"],
            "updated_at": r["updated_at"],
            "html_url": r["html_url"],
        }
        for r in repos
    ]


@mcp.tool()
def get_repo(owner: str, repo: str) -> dict:
    """Get details about a repository.

    Args:
        owner: Repository owner (user or organization login).
        repo: Repository name.
    """
    r = _request("GET", f"/repos/{owner}/{repo}")
    return {
        "full_name": r["full_name"],
        "description": r.get("description"),
        "private": r["private"],
        "default_branch": r["default_branch"],
        "language": r.get("language"),
        "topics": r.get("topics", []),
        "stars": r["stargazers_count"],
        "forks": r["forks_count"],
        "open_issues": r["open_issues_count"],
        "html_url": r["html_url"],
    }


@mcp.tool()
def search_repos(query: str, per_page: int = 10) -> list[dict]:
    """Search public repositories on GitHub.

    Args:
        query: Search query using GitHub search syntax, e.g. "mcp server language:python".
        per_page: Number of results to return (max 100).
    """
    result = _request("GET", "/search/repositories", params={"q": query, "per_page": per_page})
    return [
        {
            "full_name": r["full_name"],
            "description": r.get("description"),
            "stars": r["stargazers_count"],
            "language": r.get("language"),
            "html_url": r["html_url"],
        }
        for r in result["items"]
    ]


@mcp.tool()
def get_file_contents(owner: str, repo: str, path: str, ref: str = "") -> dict:
    """Read a file from a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        path: File path within the repository, e.g. "src/main.py".
        ref: Branch, tag, or commit SHA (defaults to the default branch).
    """
    import base64

    params = {"ref": ref} if ref else {}
    data = _request("GET", f"/repos/{owner}/{repo}/contents/{path}", params=params)
    if isinstance(data, list):
        return {
            "type": "directory",
            "entries": [{"name": e["name"], "type": e["type"], "path": e["path"]} for e in data],
        }
    content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
    return {"type": "file", "path": data["path"], "size": data["size"], "content": content}


@mcp.tool()
def list_issues(owner: str, repo: str, state: str = "open", per_page: int = 30) -> list[dict]:
    """List issues in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: Filter by state - "open", "closed", or "all".
        per_page: Number of issues to return (max 100).
    """
    issues = _request(
        "GET", f"/repos/{owner}/{repo}/issues", params={"state": state, "per_page": per_page}
    )
    return [
        {
            "number": i["number"],
            "title": i["title"],
            "state": i["state"],
            "user": i["user"]["login"],
            "labels": [l["name"] for l in i.get("labels", [])],
            "created_at": i["created_at"],
            "html_url": i["html_url"],
        }
        for i in issues
        if "pull_request" not in i  # the issues endpoint also returns PRs
    ]


@mcp.tool()
def create_issue(owner: str, repo: str, title: str, body: str = "") -> dict:
    """Create a new issue in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        title: Issue title.
        body: Issue body in Markdown (optional).
    """
    issue = _request(
        "POST", f"/repos/{owner}/{repo}/issues", json={"title": title, "body": body}
    )
    return {"number": issue["number"], "title": issue["title"], "html_url": issue["html_url"]}


@mcp.tool()
def list_pull_requests(owner: str, repo: str, state: str = "open", per_page: int = 30) -> list[dict]:
    """List pull requests in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        state: Filter by state - "open", "closed", or "all".
        per_page: Number of PRs to return (max 100).
    """
    prs = _request(
        "GET", f"/repos/{owner}/{repo}/pulls", params={"state": state, "per_page": per_page}
    )
    return [
        {
            "number": p["number"],
            "title": p["title"],
            "state": p["state"],
            "user": p["user"]["login"],
            "head": p["head"]["ref"],
            "base": p["base"]["ref"],
            "created_at": p["created_at"],
            "html_url": p["html_url"],
        }
        for p in prs
    ]


@mcp.tool()
def list_commits(owner: str, repo: str, per_page: int = 20, branch: str = "") -> list[dict]:
    """List recent commits in a repository.

    Args:
        owner: Repository owner.
        repo: Repository name.
        per_page: Number of commits to return (max 100).
        branch: Branch name (defaults to the default branch).
    """
    params: dict[str, Any] = {"per_page": per_page}
    if branch:
        params["sha"] = branch
    commits = _request("GET", f"/repos/{owner}/{repo}/commits", params=params)
    return [
        {
            "sha": c["sha"][:10],
            "message": c["commit"]["message"].splitlines()[0],
            "author": c["commit"]["author"]["name"],
            "date": c["commit"]["author"]["date"],
            "html_url": c["html_url"],
        }
        for c in commits
    ]


if __name__ == "__main__":
    mcp.run()  # stdio transport
