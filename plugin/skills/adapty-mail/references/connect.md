# Connecting the Adapty Mail MCP server

- Server URL: `https://api-mail.adapty.io/mcp`
- Transport: Streamable HTTP. Sign-in: OAuth in the browser, with dynamic client registration. No
  API key.
- Name it `adaptymail` unless the user already has another name for it.

Every client ends the same way: the browser opens the Adapty Mail dashboard, the user logs in and
clicks **Approve**. The approval screen expires after 10 minutes; past that, start the sign-in
again from the client. The user's account must be a member of the project they want to work on.

Give the user only the block for their client. Your own client is usually the one they are in;
ask if you cannot tell. You may run the shell command for them when you have a shell; the sign-in
itself is theirs.

## Claude Code

```bash
claude mcp add --transport http --scope user adaptymail https://api-mail.adapty.io/mcp
```

Sign in: `/mcp` in a session, pick `adaptymail`, **Authenticate**. Check: `claude mcp list` shows
`adaptymail` as connected; "Needs authentication" means the sign-in step is still open. Start a new
session if the tools do not appear in the current one.

Doc: https://code.claude.com/docs/en/mcp

## Codex CLI

```bash
codex mcp add adaptymail --url https://api-mail.adapty.io/mcp
codex mcp login adaptymail
```

Or add to `~/.codex/config.toml`, then run the login:

```toml
[mcp_servers.adaptymail]
url = "https://api-mail.adapty.io/mcp"
```

Check: `codex mcp list`. Start a new `codex` session to load the tools.

## GitHub Copilot CLI

```bash
copilot mcp add --transport http adaptymail https://api-mail.adapty.io/mcp
```

Or `/mcp add` inside a session (type HTTP, the URL above, save with Ctrl+S); a server added this
way is available at once. The first connection asks the user to sign in in the browser. If it
fails with 401 and never offers a sign-in, the CLI is too old for OAuth servers: update it and
retry. Check: `copilot mcp list`.

Doc: https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-mcp-servers

## Gemini CLI

```bash
gemini mcp add --transport http --scope user adaptymail https://api-mail.adapty.io/mcp
```

Or in `~/.gemini/settings.json`:

```json
{"mcpServers": {"adaptymail": {"httpUrl": "https://api-mail.adapty.io/mcp"}}}
```

Start a new session, then sign in with `/mcp auth adaptymail`. Check: `gemini mcp list`. Sign-in
needs a browser on the same machine; over SSH without port forwarding it cannot complete.

Doc: https://github.com/google-gemini/gemini-cli/blob/main/docs/tools/mcp-server.md

## Cursor, Windsurf and other JSON-configured clients

```json
{
  "mcpServers": {
    "adaptymail": {"url": "https://api-mail.adapty.io/mcp"}
  }
}
```

Cursor reads `~/.cursor/mcp.json` (every project) or `.cursor/mcp.json` (this one). VS Code uses
`"servers"` instead of `"mcpServers"` and `"type": "http"` beside the URL. Sign in from the
client's MCP settings when it asks. A client without OAuth for remote servers cannot connect.

## Claude (claude.ai and desktop) and ChatGPT

- **Claude:** Settings → Connectors → **Add custom connector**: name `Adapty Mail`, the URL above,
  keep the detected defaults, **Add**, then approve in the tab that opens.
- **ChatGPT** (developer mode on): create a custom MCP server with the URL above and OAuth,
  then approve in the tab that opens.

## When it does not connect

| Symptom | Fix |
|---|---|
| The dashboard says the request expired | Start the sign-in again from the client and approve within 10 minutes |
| The server is listed but no tools | It connected without signing in: run the client's sign-in step above |
| It worked before and now asks to sign in | Access lapsed after long idle time or a disconnect: sign in again |
| "Project not found" | The account is not a member of that project: a company owner adds them in the dashboard |

To disconnect: remove the server in the client (Claude Code: `claude mcp remove adaptymail`).
