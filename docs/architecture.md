# Architecture

`qwen_mcp.server` exposes MCP tools. `qwen_mcp.agent` owns the bounded read-only agent loop. `qwen_mcp.llama_client` is the only component that talks to llama.cpp. `qwen_mcp.repo_tools` is the only component allowed to inspect a target workspace.

The design deliberately separates inference from repository access: the model can request only named operations, while the bridge validates paths and command arguments before execution.
