import sys
import os
import traceback
import json
from typing import Any, List, Dict, Optional
from mcp.server.fastmcp import FastMCP
from notion_client import Client
from dotenv import load_dotenv

class NotionMCP:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Initialize MCP Server
        self.mcp = FastMCP("notion_mcp")
        print("MCP Server initialized", file=sys.stderr)
        
        # Initialize Notion client
        self._init_notion()
        
        # Register MCP tools
        self._register_tools()
        
        # Add debug info
        self._print_debug_info()
    
    def _print_debug_info(self):
        """Print debug information to help with troubleshooting."""
        print("=" * 50, file=sys.stderr)
        print("DEBUG INFO:", file=sys.stderr)
        print(f"Python version: {sys.version}", file=sys.stderr)
        print(f"Working directory: {os.getcwd()}", file=sys.stderr)
        print(f"Script path: {__file__}", file=sys.stderr)
        print(f"Environment variables loaded:", file=sys.stderr)
        print(f"  NOTION_API_KEY: {'SET' if os.getenv('NOTION_API_KEY') else 'NOT SET'}", file=sys.stderr)
        print("=" * 50, file=sys.stderr)
    
    def _init_notion(self):
        """Initialize the Notion client with API key and parent page ID."""
        try:
            self.notion_api_key = os.getenv("NOTION_API_KEY")
            self.notion_parent_id = os.getenv("NOTION_PARENT_ID", os.getenv("NOTION_PARENT_ID"))
            if not self.notion_api_key:
                raise ValueError("Missing Notion API key in environment variables")
            if not self.notion_parent_id:
                print("Warning: NOTION_PARENT_ID is not set. Notion page creation will fail.", file=sys.stderr)
            self.notion = Client(auth=self.notion_api_key)
            print(f"Notion client initialized successfully", file=sys.stderr)
            print(f"Using Notion parent page ID: {self.notion_parent_id}", file=sys.stderr)
        except Exception as e:
            print(f"Error initializing Notion client: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)
    
    def _get_workspace_id(self):
        """Get the workspace ID for creating root-level pages."""
        try:
            # List all pages to find a workspace
            search_results = self.notion.search(filter={"property": "object", "value": "page"})
            if search_results.get("results"):
                for page in search_results["results"]:
                    if page.get("parent", {}).get("type") == "workspace":
                        return {"type": "workspace", "workspace": True}
            return None
        except Exception as e:
            print(f"Error getting workspace ID: {str(e)}", file=sys.stderr)
            return None
    
    def _search_notion_page(self, title: str) -> Optional[str]:
        """Search for a Notion page by title and return its ID if found."""
        try:
            print(f"Searching for Notion page with title: {title}", file=sys.stderr)
            search_results = self.notion.search(
                query=title,
                filter={"property": "object", "value": "page"}
            )
            
            if search_results.get("results"):
                for page in search_results["results"]:
                    page_title = ""
                    if page.get("properties", {}).get("title", {}).get("title"):
                        page_title = page["properties"]["title"]["title"][0]["text"]["content"]
                    elif page.get("properties", {}).get("Name", {}).get("title"):
                        page_title = page["properties"]["Name"]["title"][0]["text"]["content"]
                    
                    if page_title.lower() == title.lower():
                        page_id = page["id"]
                        print(f"Found existing page with ID: {page_id}", file=sys.stderr)
                        return page_id
            
            print(f"No existing page found with title: {title}", file=sys.stderr)
            return None
            
        except Exception as e:
            print(f"Error searching for Notion page: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return None
    
    def _create_notion_page(self, title: str, content: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a new Notion page with the given title and content."""
        try:
            parent = {"type": "page_id", "page_id": parent_id or self.notion_parent_id}
            
            # Convert content to Notion blocks
            blocks = self._content_to_notion_blocks(content)
            
            response = self.notion.pages.create(
                parent=parent,
                properties={
                    "title": {
                        "title": [
                            {"text": {"content": title}}
                        ]
                    }
                },
                children=blocks
            )
            
            page_url = response.get("url", "No URL available")
            page_id = response.get("id", "No ID available")
            
            print(f"Created new Notion page with ID: {page_id}", file=sys.stderr)
            return {
                "success": True,
                "page_id": page_id,
                "page_url": page_url,
                "action": "created"
            }
            
        except Exception as e:
            error_msg = f"Error creating Notion page: {str(e)}"
            print(error_msg, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {"success": False, "error": error_msg}
    
    def _delete_all_blocks(self, page_id: str) -> bool:
        """Delete all blocks from a Notion page."""
        try:
            print(f"Deleting all blocks from page: {page_id}", file=sys.stderr)
            
            # Get all child blocks
            blocks_response = self.notion.blocks.children.list(block_id=page_id)
            blocks = blocks_response.get("results", [])
            
            # Delete each block
            for block in blocks:
                block_id = block.get("id")
                if block_id:
                    try:
                        self.notion.blocks.delete(block_id=block_id)
                        print(f"Deleted block: {block_id}", file=sys.stderr)
                    except Exception as e:
                        print(f"Error deleting block {block_id}: {str(e)}", file=sys.stderr)
                        # Continue with other blocks even if one fails
            
            print(f"Successfully deleted {len(blocks)} blocks", file=sys.stderr)
            return True
            
        except Exception as e:
            print(f"Error deleting blocks: {str(e)}", file=sys.stderr)
            return False
    
    def _update_notion_page(self, page_id: str, title: str, content: str) -> Dict[str, Any]:
        """Append content to an existing Notion page (continuous writing)."""
        try:
            print(f"Appending to Notion page: {page_id}", file=sys.stderr)
            
            # Only update title if it's different (optional - use this if you want to change titles)
            # Note: Uncomment the next block if you want to update the title
            # self.notion.pages.update(
            #     page_id=page_id,
            #     properties={
            #         "title": {
            #             "title": [
            #                 {"text": {"content": title}}
            #             ]
            #         }
            #     }
            # )
            
            # Convert content to Notion blocks
            blocks = self._content_to_notion_blocks(content)
            
            # Append new content in batches (Notion API has a limit of 100 blocks per request)
            if blocks:
                batch_size = 100
                for i in range(0, len(blocks), batch_size):
                    batch = blocks[i:i+batch_size]
                    try:
                        self.notion.blocks.children.append(
                            block_id=page_id, 
                            children=batch
                        )
                        print(f"Appended batch of {len(batch)} blocks", file=sys.stderr)
                    except Exception as e:
                        print(f"Error appending batch {i//batch_size + 1}: {str(e)}", file=sys.stderr)
                        # Continue with next batch
            
            page_url = f"https://notion.so/{page_id.replace('-', '')}"
            
            print(f"Successfully appended to Notion page with ID: {page_id}", file=sys.stderr)
            return {
                "success": True,
                "page_id": page_id,
                "page_url": page_url,
                "action": "appended"
            }
            
        except Exception as e:
            error_msg = f"Error appending to Notion page: {str(e)}"
            print(error_msg, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {"success": False, "error": error_msg}
    
    def _append_to_notion_page(self, page_id: str, content: str) -> Dict[str, Any]:
        """Append content to an existing Notion page without deleting existing content."""
        try:
            print(f"Appending to Notion page: {page_id}", file=sys.stderr)
            
            # Convert content to Notion blocks
            blocks = self._content_to_notion_blocks(content)
            
            # Add new content in batches
            if blocks:
                batch_size = 100
                for i in range(0, len(blocks), batch_size):
                    batch = blocks[i:i+batch_size]
                    try:
                        self.notion.blocks.children.append(
                            block_id=page_id, 
                            children=batch
                        )
                        print(f"Appended batch of {len(batch)} blocks", file=sys.stderr)
                    except Exception as e:
                        print(f"Error appending batch {i//batch_size + 1}: {str(e)}", file=sys.stderr)
                        # Continue with next batch
            
            page_url = f"https://notion.so/{page_id.replace('-', '')}"
            
            print(f"Successfully appended to Notion page with ID: {page_id}", file=sys.stderr)
            return {
                "success": True,
                "page_id": page_id,
                "page_url": page_url,
                "action": "appended"
            }
            
        except Exception as e:
            error_msg = f"Error appending to Notion page: {str(e)}"
            print(error_msg, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return {"success": False, "error": error_msg}
    
    def _content_to_notion_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Convert plain text content to Notion block format."""
        blocks = []
        
        # Split content by lines and create blocks
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip empty lines
            if not line:
                i += 1
                continue
            
            # Handle code blocks
            if line.startswith('```'):
                # Multi-line code block
                language = line[3:].strip() if len(line) > 3 else ""
                code_content = []
                i += 1
                
                # Collect all lines until closing ```
                while i < len(lines) and not lines[i].strip().startswith('```'):
                    code_content.append(lines[i])
                    i += 1
                
                # Skip the closing ```
                if i < len(lines) and lines[i].strip().startswith('```'):
                    i += 1
                
                # Create code block
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "language": language or "plain text",
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": "\n".join(code_content)}
                        }]
                    }
                })
                continue
            
            # Handle other block types
            if line.startswith('# '):
                # Heading 1
                blocks.append({
                    "object": "block",
                    "type": "heading_1",
                    "heading_1": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": line[2:]}
                        }]
                    }
                })
            elif line.startswith('## '):
                # Heading 2
                blocks.append({
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": line[3:]}
                        }]
                    }
                })
            elif line.startswith('### '):
                # Heading 3
                blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": line[4:]}
                        }]
                    }
                })
            elif line.startswith('- ') or line.startswith('* '):
                # Bullet list
                blocks.append({
                    "object": "block",
                    "type": "bulleted_list_item",
                    "bulleted_list_item": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": line[2:]}
                        }]
                    }
                })
            elif any(line.startswith(f"{j}. ") for j in range(1, 10)):
                # Numbered list (1. to 9.)
                space_index = line.find('. ')
                if space_index != -1:
                    content = line[space_index + 2:]
                    blocks.append({
                        "object": "block",
                        "type": "numbered_list_item",
                        "numbered_list_item": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": content}
                            }]
                        }
                    })
            else:
                # Regular paragraph
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{
                            "type": "text",
                            "text": {"content": line}
                        }]
                    }
                })
            
            i += 1
        
        return blocks
    
    def _register_tools(self):
        """Register MCP tools for PR analysis."""
        print("Registering MCP tools...", file=sys.stderr)
        
        @self.mcp.tool()
        async def create_notion_page(title: str, content: str) -> str:
            """Create a Notion page with PR analysis under a specific parent page."""
            print(f"Tool called: create_notion_page({title})", file=sys.stderr)
            try:
                parent = {"type": "page_id", "page_id": self.notion_parent_id}
                response = self.notion.pages.create(
                    parent=parent,
                    properties={
                        "title": {
                            "title": [
                                {"text": {"content": title}}
                            ]
                        }
                    },
                    children=[{
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{
                                "type": "text",
                                "text": {"content": content}
                            }]
                        }
                    }]
                )
                page_url = response.get("url", "No URL available")
                success_msg = f"Notion page '{title}' created successfully! URL: {page_url}"
                print(success_msg, file=sys.stderr)
                return success_msg
            except Exception as e:
                error_msg = f"Error creating Notion page: {str(e)}"
                print(error_msg, file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return error_msg
        
        @self.mcp.tool()
        async def write_to_notion(title: str, content: str, parent_id: Optional[str] = None, mode: str = "replace") -> Dict[str, Any]:
            """Write content to Notion - creates new page if it doesn't exist, updates existing page if it does.
            
            Args:
                title: The title of the page
                content: The content to write
                parent_id: Optional parent page ID
                mode: 'replace' (default) to replace all content, 'append' to add to existing content
            """
            print(f"Tool called: write_to_notion({title}, mode={mode})", file=sys.stderr)
            try:
                # Search for existing page
                existing_page_id = self._search_notion_page(title)
                
                if existing_page_id:
                    if mode == "append":
                        # Append to existing page
                        result = self._append_to_notion_page(existing_page_id, content)
                        if result["success"]:
                            return {
                                "status": "appended",
                                "message": f"Appended content to existing Notion page '{title}'",
                                "page_id": result["page_id"],
                                "page_url": result["page_url"]
                            }
                        else:
                            return {"error": result["error"]}
                    else:
                        # Append to existing page
                        result = self._update_notion_page(existing_page_id, title, content)
                        if result["success"]:
                            return {
                                "status": "appended",
                                "message": f"Appended content to existing Notion page '{title}'",
                                "page_id": result["page_id"],
                                "page_url": result["page_url"]
                            }
                        else:
                            return {"error": result["error"]}
                else:
                    # Create new page
                    result = self._create_notion_page(title, content, parent_id)
                    if result["success"]:
                        return {
                            "status": "created",
                            "message": f"Created new Notion page '{title}'",
                            "page_id": result["page_id"],
                            "page_url": result["page_url"]
                        }
                    else:
                        return {"error": result["error"]}
                        
            except Exception as e:
                error_msg = f"Error writing to Notion: {str(e)}"
                print(error_msg, file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return {"error": error_msg}
        
        @self.mcp.tool()
        async def append_to_notion(title: str, content: str, parent_id: Optional[str] = None) -> Dict[str, Any]:
            """Append content to an existing Notion page or create a new one if it doesn't exist."""
            print(f"Tool called: append_to_notion({title})", file=sys.stderr)
            try:
                # Search for existing page
                existing_page_id = self._search_notion_page(title)
                
                if existing_page_id:
                    # Append to existing page
                    result = self._append_to_notion_page(existing_page_id, content)
                    if result["success"]:
                        return {
                            "status": "appended",
                            "message": f"Appended content to existing Notion page '{title}'",
                            "page_id": result["page_id"],
                            "page_url": result["page_url"]
                        }
                    else:
                        return {"error": result["error"]}
                else:
                    # Create new page
                    result = self._create_notion_page(title, content, parent_id)
                    if result["success"]:
                        return {
                            "status": "created",
                            "message": f"Created new Notion page '{title}'",
                            "page_id": result["page_id"],
                            "page_url": result["page_url"]
                        }
                    else:
                        return {"error": result["error"]}
                        
            except Exception as e:
                error_msg = f"Error appending to Notion: {str(e)}"
                print(error_msg, file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return {"error": error_msg}
        
        @self.mcp.tool()
        async def search_notion_pages(query: str) -> Dict[str, Any]:
            """Search for Notion pages by title or content."""
            print(f"Tool called: search_notion_pages({query})", file=sys.stderr)
            try:
                search_results = self.notion.search(
                    query=query,
                    filter={"property": "object", "value": "page"}
                )
                
                pages = []
                if search_results.get("results"):
                    for page in search_results["results"]:
                        page_info = {
                            "id": page["id"],
                            "url": page.get("url", ""),
                            "title": "",
                            "created_time": page.get("created_time", ""),
                            "last_edited_time": page.get("last_edited_time", "")
                        }
                        
                        # Extract title from properties
                        if page.get("properties", {}).get("title", {}).get("title"):
                            page_info["title"] = page["properties"]["title"]["title"][0]["text"]["content"]
                        elif page.get("properties", {}).get("Name", {}).get("title"):
                            page_info["title"] = page["properties"]["Name"]["title"][0]["text"]["content"]
                        
                        pages.append(page_info)
                
                return {
                    "query": query,
                    "total_results": len(pages),
                    "pages": pages
                }
                
            except Exception as e:
                error_msg = f"Error searching Notion pages: {str(e)}"
                print(error_msg, file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return {"error": error_msg}
        
        @self.mcp.tool()
        async def get_notion_page_content(page_id: str) -> Dict[str, Any]:
            """Get the content of a specific Notion page by ID."""
            print(f"Tool called: get_notion_page_content({page_id})", file=sys.stderr)
            try:
                # Get page properties
                page = self.notion.pages.retrieve(page_id=page_id)
                
                # Get page blocks (content)
                blocks = self.notion.blocks.children.list(block_id=page_id)
                
                # Extract title
                title = ""
                if page.get("properties", {}).get("title", {}).get("title"):
                    title = page["properties"]["title"]["title"][0]["text"]["content"]
                elif page.get("properties", {}).get("Name", {}).get("title"):
                    title = page["properties"]["Name"]["title"][0]["text"]["content"]
                
                # Convert blocks to readable content
                content_lines = []
                for block in blocks.get("results", []):
                    block_type = block.get("type", "")
                    if block_type == "paragraph" and block.get("paragraph", {}).get("rich_text"):
                        if block["paragraph"]["rich_text"]:
                            text = block["paragraph"]["rich_text"][0]["text"]["content"]
                            content_lines.append(text)
                    elif block_type == "heading_1" and block.get("heading_1", {}).get("rich_text"):
                        if block["heading_1"]["rich_text"]:
                            text = f"# {block['heading_1']['rich_text'][0]['text']['content']}"
                            content_lines.append(text)
                    elif block_type == "heading_2" and block.get("heading_2", {}).get("rich_text"):
                        if block["heading_2"]["rich_text"]:
                            text = f"## {block['heading_2']['rich_text'][0]['text']['content']}"
                            content_lines.append(text)
                    elif block_type == "heading_3" and block.get("heading_3", {}).get("rich_text"):
                        if block["heading_3"]["rich_text"]:
                            text = f"### {block['heading_3']['rich_text'][0]['text']['content']}"
                            content_lines.append(text)
                    elif block_type == "bulleted_list_item" and block.get("bulleted_list_item", {}).get("rich_text"):
                        if block["bulleted_list_item"]["rich_text"]:
                            text = f"- {block['bulleted_list_item']['rich_text'][0]['text']['content']}"
                            content_lines.append(text)
                    elif block_type == "numbered_list_item" and block.get("numbered_list_item", {}).get("rich_text"):
                        if block["numbered_list_item"]["rich_text"]:
                            text = f"1. {block['numbered_list_item']['rich_text'][0]['text']['content']}"
                            content_lines.append(text)
                    elif block_type == "code" and block.get("code", {}).get("rich_text"):
                        if block["code"]["rich_text"]:
                            language = block["code"].get("language", "")
                            text = f"```{language}\n{block['code']['rich_text'][0]['text']['content']}\n```"
                            content_lines.append(text)
                
                content = "\n".join(content_lines)
                
                return {
                    "page_id": page_id,
                    "title": title,
                    "url": page.get("url", ""),
                    "content": content,
                    "created_time": page.get("created_time", ""),
                    "last_edited_time": page.get("last_edited_time", "")
                }
                
            except Exception as e:
                error_msg = f"Error getting Notion page content: {str(e)}"
                print(error_msg, file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                return {"error": error_msg}
        
        @self.mcp.tool()
        async def test_connection() -> str:
            """Test tool to verify MCP connection is working."""
            print("Tool called: test_connection()", file=sys.stderr)
            return "MCP connection is working! Server is responding to tool calls."
        
        print("MCP tools registered successfully!", file=sys.stderr)
    
    def run(self):
        """Start the MCP server."""
        try:
            print("Server is ready to accept connections via stdio", file=sys.stderr)
            
            # This will block and handle stdio communication
            self.mcp.run(transport="stdio")
            
        except KeyboardInterrupt:
            print("Server stopped by user", file=sys.stderr)
        except Exception as e:
            print(f"Fatal Error in MCP Server: {str(e)}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    try:
        notionMCP = NotionMCP()
        notionMCP.run()
    except Exception as e:
        print(f"Failed to start Notion MCP server: {str(e)}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)