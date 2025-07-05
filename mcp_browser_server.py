#!/usr/bin/env python3
"""
MCP Server for browser automation testing using Playwright.
Allows direct testing of the journal app's functionality.
"""

import asyncio
import json
import logging
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR
)
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserTestServer:
    def __init__(self):
        self.server = Server("browser-test")
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        
        # Register handlers
        self.server.list_tools = self.list_tools
        self.server.call_tool = self.call_tool
    
    async def list_tools(self, request: ListToolsRequest) -> ListToolsResult:
        """List available testing tools."""
        return ListToolsResult(
            tools=[
                Tool(
                    name="start_browser",
                    description="Start a browser session for testing",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "headless": {
                                "type": "boolean",
                                "description": "Run browser in headless mode",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="navigate_to_page",
                    description="Navigate to a specific page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "URL to navigate to"
                            }
                        },
                        "required": ["url"]
                    }
                ),
                Tool(
                    name="test_location_search",
                    description="Test the location search functionality",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "search_term": {
                                "type": "string",
                                "description": "Location to search for"
                            },
                            "page_url": {
                                "type": "string",
                                "description": "URL of the page to test on",
                                "default": "https://journal.joshsisto.com/journal/quick"
                            }
                        },
                        "required": ["search_term"]
                    }
                ),
                Tool(
                    name="check_console_errors",
                    description="Check for JavaScript console errors",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                Tool(
                    name="get_page_content",
                    description="Get the current page content",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector to get specific content",
                                "default": "body"
                            }
                        }
                    }
                ),
                Tool(
                    name="click_element",
                    description="Click on an element",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the element to click"
                            }
                        },
                        "required": ["selector"]
                    }
                ),
                Tool(
                    name="type_text",
                    description="Type text into an input field",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the input field"
                            },
                            "text": {
                                "type": "string",
                                "description": "Text to type"
                            }
                        },
                        "required": ["selector", "text"]
                    }
                ),
                Tool(
                    name="wait_for_element",
                    description="Wait for an element to appear",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "selector": {
                                "type": "string",
                                "description": "CSS selector for the element to wait for"
                            },
                            "timeout": {
                                "type": "number",
                                "description": "Timeout in milliseconds",
                                "default": 5000
                            }
                        },
                        "required": ["selector"]
                    }
                ),
                Tool(
                    name="screenshot",
                    description="Take a screenshot of the current page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Filename for the screenshot",
                                "default": "screenshot.png"
                            }
                        }
                    }
                ),
                Tool(
                    name="close_browser",
                    description="Close the browser session",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                )
            ]
        )
    
    async def call_tool(self, request: CallToolRequest) -> CallToolResult:
        """Handle tool calls."""
        try:
            name = request.params.name
            arguments = request.params.arguments or {}
            
            if name == "start_browser":
                return await self.start_browser(arguments)
            elif name == "navigate_to_page":
                return await self.navigate_to_page(arguments)
            elif name == "test_location_search":
                return await self.test_location_search(arguments)
            elif name == "check_console_errors":
                return await self.check_console_errors(arguments)
            elif name == "get_page_content":
                return await self.get_page_content(arguments)
            elif name == "click_element":
                return await self.click_element(arguments)
            elif name == "type_text":
                return await self.type_text(arguments)
            elif name == "wait_for_element":
                return await self.wait_for_element(arguments)
            elif name == "screenshot":
                return await self.screenshot(arguments)
            elif name == "close_browser":
                return await self.close_browser(arguments)
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                    isError=True
                )
        except Exception as e:
            logger.error(f"Error in call_tool: {e}")
            logger.error(traceback.format_exc())
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error: {str(e)}")],
                isError=True
            )
    
    async def start_browser(self, arguments: dict) -> CallToolResult:
        """Start a browser session."""
        try:
            headless = arguments.get("headless", True)
            
            if self.playwright is None:
                self.playwright = await async_playwright().start()
            
            if self.browser is None:
                self.browser = await self.playwright.chromium.launch(
                    headless=headless,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            
            if self.context is None:
                self.context = await self.browser.new_context(
                    ignore_https_errors=True,
                    viewport={'width': 1280, 'height': 720}
                )
            
            if self.page is None:
                self.page = await self.context.new_page()
                
                # Capture console messages
                self.console_messages = []
                self.page.on('console', lambda msg: self.console_messages.append({
                    'type': msg.type,
                    'text': msg.text,
                    'location': msg.location
                }))
                
                # Capture network errors
                self.page.on('pageerror', lambda error: self.console_messages.append({
                    'type': 'error',
                    'text': str(error),
                    'location': 'page'
                }))
            
            return CallToolResult(
                content=[TextContent(type="text", text="Browser started successfully")]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Failed to start browser: {str(e)}")],
                isError=True
            )
    
    async def navigate_to_page(self, arguments: dict) -> CallToolResult:
        """Navigate to a specific page."""
        try:
            if self.page is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="Browser not started. Call start_browser first.")],
                    isError=True
                )
            
            url = arguments["url"]
            await self.page.goto(url, wait_until="networkidle")
            
            title = await self.page.title()
            return CallToolResult(
                content=[TextContent(type="text", text=f"Navigated to: {url}\nPage title: {title}")]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Navigation failed: {str(e)}")],
                isError=True
            )
    
    async def test_location_search(self, arguments: dict) -> CallToolResult:
        """Test the location search functionality."""
        try:
            if self.page is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="Browser not started. Call start_browser first.")],
                    isError=True
                )
            
            search_term = arguments["search_term"]
            page_url = arguments.get("page_url", "https://journal.joshsisto.com/journal/quick")
            
            # Navigate to the page if not already there
            current_url = self.page.url
            if not current_url.startswith(page_url):
                await self.page.goto(page_url, wait_until="networkidle")
            
            # Wait for the location search input to be available
            search_input_selector = "#location-search-input"
            search_button_selector = "#search-location-btn"
            
            await self.page.wait_for_selector(search_input_selector, timeout=10000)
            
            # Clear any existing text and type the search term
            await self.page.fill(search_input_selector, "")
            await self.page.type(search_input_selector, search_term)
            
            # Click the search button
            await self.page.click(search_button_selector)
            
            # Wait a moment for any response
            await self.page.wait_for_timeout(2000)
            
            # Check for status messages
            status_messages = []
            try:
                status_element = await self.page.query_selector("#location-status")
                if status_element:
                    status_text = await status_element.inner_text()
                    status_messages.append(f"Status: {status_text}")
            except:
                pass
            
            # Check for location display
            location_display = []
            try:
                display_element = await self.page.query_selector("#location-display")
                if display_element:
                    display_text = await display_element.inner_text()
                    location_display.append(f"Location display: {display_text}")
            except:
                pass
            
            # Check console for errors
            recent_console = [msg for msg in self.console_messages[-10:]]
            
            result_text = f"""Location Search Test Results:
Search Term: {search_term}
Page URL: {page_url}

Status Messages: {'; '.join(status_messages) if status_messages else 'None found'}
Location Display: {'; '.join(location_display) if location_display else 'None found'}

Recent Console Messages:
{json.dumps(recent_console, indent=2) if recent_console else 'No recent console messages'}
"""
            
            return CallToolResult(
                content=[TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Location search test failed: {str(e)}")],
                isError=True
            )
    
    async def check_console_errors(self, arguments: dict) -> CallToolResult:
        """Check for JavaScript console errors."""
        try:
            if self.page is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="Browser not started. Call start_browser first.")],
                    isError=True
                )
            
            errors = [msg for msg in self.console_messages if msg['type'] == 'error']
            warnings = [msg for msg in self.console_messages if msg['type'] == 'warning']
            
            result = f"""Console Analysis:
Errors: {len(errors)}
Warnings: {len(warnings)}
Total Messages: {len(self.console_messages)}

Recent Errors:
{json.dumps(errors[-5:], indent=2) if errors else 'No errors'}

Recent Warnings:
{json.dumps(warnings[-5:], indent=2) if warnings else 'No warnings'}
"""
            
            return CallToolResult(
                content=[TextContent(type="text", text=result)]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Console check failed: {str(e)}")],
                isError=True
            )
    
    async def get_page_content(self, arguments: dict) -> CallToolResult:
        """Get page content."""
        try:
            if self.page is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="Browser not started. Call start_browser first.")],
                    isError=True
                )
            
            selector = arguments.get("selector", "body")
            element = await self.page.query_selector(selector)
            
            if element:
                content = await element.inner_text()
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Content from '{selector}':\n{content[:1000]}...")]
                )
            else:
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Element '{selector}' not found")],
                    isError=True
                )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Get content failed: {str(e)}")],
                isError=True
            )
    
    async def click_element(self, arguments: dict) -> CallToolResult:
        """Click on an element."""
        try:
            if self.page is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="Browser not started. Call start_browser first.")],
                    isError=True
                )
            
            selector = arguments["selector"]
            await self.page.click(selector)
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"Clicked element: {selector}")]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Click failed: {str(e)}")],
                isError=True
            )
    
    async def type_text(self, arguments: dict) -> CallToolResult:
        """Type text into an input field."""
        try:
            if self.page is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="Browser not started. Call start_browser first.")],
                    isError=True
                )
            
            selector = arguments["selector"]
            text = arguments["text"]
            
            await self.page.fill(selector, text)
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"Typed '{text}' into {selector}")]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Type failed: {str(e)}")],
                isError=True
            )
    
    async def wait_for_element(self, arguments: dict) -> CallToolResult:
        """Wait for an element to appear."""
        try:
            if self.page is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="Browser not started. Call start_browser first.")],
                    isError=True
                )
            
            selector = arguments["selector"]
            timeout = arguments.get("timeout", 5000)
            
            await self.page.wait_for_selector(selector, timeout=timeout)
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"Element {selector} appeared")]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Wait failed: {str(e)}")],
                isError=True
            )
    
    async def screenshot(self, arguments: dict) -> CallToolResult:
        """Take a screenshot."""
        try:
            if self.page is None:
                return CallToolResult(
                    content=[TextContent(type="text", text="Browser not started. Call start_browser first.")],
                    isError=True
                )
            
            filename = arguments.get("filename", "screenshot.png")
            await self.page.screenshot(path=filename)
            
            return CallToolResult(
                content=[TextContent(type="text", text=f"Screenshot saved as {filename}")]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Screenshot failed: {str(e)}")],
                isError=True
            )
    
    async def close_browser(self, arguments: dict) -> CallToolResult:
        """Close the browser session."""
        try:
            if self.page:
                await self.page.close()
                self.page = None
            
            if self.context:
                await self.context.close()
                self.context = None
            
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
            
            return CallToolResult(
                content=[TextContent(type="text", text="Browser closed successfully")]
            )
        except Exception as e:
            return CallToolResult(
                content=[TextContent(type="text", text=f"Close browser failed: {str(e)}")],
                isError=True
            )

async def main():
    """Run the MCP server."""
    server_instance = BrowserTestServer()
    
    async with stdio_server() as streams:
        await server_instance.server.run(
            streams[0], 
            streams[1], 
            server_instance.server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())