# NotionMCP Server

A Python server that integrates [MCP](https://github.com/microsoft/mcp) with [Notion](https://www.notion.so/) to automate PR analysis and documentation workflows.

## Features

- Exposes MCP tools for creating, updating, and searching Notion pages
- Converts plain text and markdown-like content into Notion blocks
- Supports appending and replacing content in Notion pages
- Provides debug information for troubleshooting

## Requirements

- Python 3.10+
- Notion integration token and parent page ID
- MCP server and CLI
- See [requirements.txt](requirements.txt) for Python dependencies

## Setup

1. **Clone the repository** and navigate to the project directory.

2. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   - Find the related API key and parent page ID from your Notion
   - API key is the integration key
   - Parent page ID is the target page we use to interact with LLMs prompt
   - Set `NOTION_API_KEY` and `NOTION_PARENT_ID` in `.env` file

4. **Run the server**:
   ```sh
   python notionMCP_server.py
   ```

5. **Edit LLMs config file to recognize MCP server**:
   - In this project, I used Claude desktop, here is how to edit the config
   - Find `claude_desktop_config.json` and edit as follows:
   ```json
   {
     "mcpServers": {
       "NotionMCP": {
         "command": "path_to_the_exe_python_file_running_your_server",
         "args": ["path_to_python_server_file(notionMCP_server.py)"],
         "env": {}
       }
     }
   }
   ```
   - Use `which python` to find the executable python file running your server

## License

MIT License