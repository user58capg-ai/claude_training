# GitHub MCP Server

A Python MCP (Model Context Protocol) server that connects Claude to GitHub.
It exposes GitHub REST API operations as tools over stdio.

## Tools

| Tool | Description |
|---|---|
| `get_authenticated_user` | Verify the token works; show your profile |
| `list_repos` | List your repositories |
| `get_repo` | Get details for one repository |
| `search_repos` | Search public repositories |
| `get_file_contents` | Read a file (or list a directory) in a repo |
| `list_issues` | List issues in a repo |
| `create_issue` | Create a new issue |
| `list_pull_requests` | List pull requests |
| `list_commits` | List recent commits |

## Setup

### 1. Install dependencies

```powershell
cd c:\Users\Admin\Documents\Claude_Training\github_mcp_server
pip install -r requirements.txt
```

### 2. Create a GitHub Personal Access Token

1. Go to https://github.com/settings/tokens
2. Generate a new token (classic) with the `repo` scope
   (or a fine-grained token with Contents: Read, Issues: Read and write)
3. Paste it into the `.env` file in this folder:

```
GITHUB_TOKEN=ghp_your_actual_token
```

The server loads `.env` automatically at startup. Never commit this file (it's in `.gitignore`).

### 3. Register with Claude Code

```powershell
claude mcp add github -- python "c:\Users\Admin\Documents\Claude_Training\github_mcp_server\server.py"
```

Then restart Claude Code and run `/mcp` to confirm the `github` server is connected.

### Claude Desktop (alternative)

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "python",
      "args": ["c:\\Users\\Admin\\Documents\\Claude_Training\\github_mcp_server\\server.py"]
    }
  }
}
```

(The token comes from `.env`, so no `env` block is needed.)

## Try it

Once connected, ask Claude things like:

- "Who am I on GitHub?" → `get_authenticated_user`
- "List my repos" → `list_repos`
- "Search GitHub for MCP servers written in Python" → `search_repos`
- "Show the README of anthropics/anthropic-sdk-python" → `get_file_contents`
- "Create an issue in my-org/my-repo titled 'Bug: ...'" → `create_issue`

## Development / debugging

Run the MCP Inspector to test tools interactively without Claude:

```powershell
npx @modelcontextprotocol/inspector python server.py
```
