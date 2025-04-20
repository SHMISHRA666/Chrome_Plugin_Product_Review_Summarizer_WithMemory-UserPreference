"""
Product Review Summariser - Main Module

This module configures and runs the Product Review Summariser agent.
It initializes all cognitive layers and starts the web server.
"""

import os
import asyncio
import logging
from dotenv import load_dotenv
from google import genai
from aiohttp import web
from rich.console import Console
from rich.panel import Panel
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import json

from perception_layer import PerceptionLayer
from memory_layer import MemoryLayer
from decision_layer import DecisionLayer
from action_layer import ActionLayer

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize rich console for formatted output
console = Console()

async def start_server_with_mcp():
    """
    Start the API server with MCP integration
    
    This function:
    1. Initializes the MCP client to communicate with the server
    2. Sets up an aiohttp web server with API routes
    3. Configures CORS for cross-origin requests from the extension
    4. Runs the server in a blocking manner until interrupted
    """
    try:
        console.print(Panel("Product Review Summariser API Server", border_style="cyan"))
        
        # Create the MCP client parameters to connect to the server
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"],
            encoding_error_handler="replace"
        )
        
        # Initialize aiohttp web application
        logger.info("Starting MCP client...")
        app = web.Application()
        
        # Start MCP client and server in one process
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Initialize cognitive layers
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                perception_layer = PerceptionLayer(client)
                memory_layer = MemoryLayer()
                decision_layer = DecisionLayer(client)
                action_layer = ActionLayer(perception_layer, memory_layer, decision_layer)
                
                # Set MCP session for all layers
                perception_layer.session = session
                decision_layer.session = session
                action_layer.session = session
                
                # Setup API routes
                action_layer.setup_routes(app)
                
                # Start the web server
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, 'localhost', 8080)
                await site.start()
                
                console.print(Panel(f"Server started at http://localhost:8080", border_style="green"))
                
                # Keep the server running until interrupted
                try:
                    # Run forever
                    while True:
                        await asyncio.sleep(3600)  # Sleep for an hour
                except asyncio.CancelledError:
                    pass
                finally:
                    await runner.cleanup()
    
    except Exception as e:
        logger.error(f"Error starting server: {e}", exc_info=True)
        console.print(f"[red]Error: {e}[/red]")

async def main():
    """
    Test function for direct execution with a sample product
    
    This function:
    1. Initializes the MCP client to communicate with the server
    2. Processes a sample product (Samsung Galaxy S23 Ultra)
    3. Displays the results in the console
    """
    try:
        console.print(Panel("Product Review Summariser", border_style="cyan"))

        # Setup MCP client parameters
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"],
            encoding_error_handler="replace"
        )

        # Start MCP client
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Initialize cognitive layers
                client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
                perception_layer = PerceptionLayer(client)
                memory_layer = MemoryLayer()
                decision_layer = DecisionLayer(client)
                action_layer = ActionLayer(perception_layer, memory_layer, decision_layer)
                
                # Set MCP session for all layers
                perception_layer.session = session
                decision_layer.session = session
                action_layer.session = session
                
                # Example product data for testing
                example_product = {
                    "title": "Samsung Galaxy S23 Ultra",
                    "site": "amazon.com",
                    "price": "$1199.99",
                    "url": "https://www.amazon.com/samsung-galaxy-s23-ultra"
                }
                
                console.print(Panel(f"Processing product: {example_product['title']}", border_style="green"))
                
                # Set product info in decision layer and action layer
                decision_layer.set_product_info(example_product)
                action_layer.set_product_info(example_product)
                
                # Process the product through all layers
                category = await perception_layer.classify_product(example_product["title"])
                decision_layer.set_category(category)  # Set the category in decision layer
                prompt = await perception_layer.craft_initial_prompt(example_product, category)
                tool_plan = await perception_layer.get_tool_invocation_plan(prompt)
                
                results = await action_layer.execute_tool_plan(tool_plan)
                self_check = await action_layer.check_tool_results(results)
                
                final_response = await decision_layer.perform_final_reasoning(results, self_check)
                memory_layer.store_product_analysis(example_product, final_response)
                
                # Display the result
                console.print(Panel(json.dumps(final_response, indent=2), border_style="cyan", title="Analysis Result"))

    except Exception as e:
        logger.error(f"Error in main function: {e}", exc_info=True)
        console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    """
    Entry point with command-line argument parsing
    
    Supports three modes:
    1. Server mode (--server): Run as API server for Chrome extension
    2. Test mode (--test): Run with sample product for testing
    3. Default mode: Run as API server (same as --server)
    
    Also supports debug mode (--debug) for detailed logging
    """
    import argparse
    
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Product Review Summariser")
    parser.add_argument("--server", action="store_true", help="Start in server mode for Chrome extension")
    parser.add_argument("--test", action="store_true", help="Run a test analysis with example product")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging to server_debug.log")
    
    args = parser.parse_args()
    
    # Set debug environment variable if enabled
    if args.debug:
        os.environ["SPA_DEBUG"] = "1"
        print("Debug logging enabled - check server_debug.log for server output")
    
    if args.server:
        # Start server for Chrome extension
        print("Starting server for Chrome extension")
        asyncio.run(start_server_with_mcp())
    elif args.test:
        # Run test with example product
        print("Running test with example product")
        asyncio.run(main())
    else:
        # Default to server mode
        print("Starting server in default mode")
        asyncio.run(start_server_with_mcp())
