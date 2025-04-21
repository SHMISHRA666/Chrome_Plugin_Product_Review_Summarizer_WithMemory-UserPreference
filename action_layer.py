"""
Smart Purchase Advisor - Action Layer

This module handles API routes and server communication.
It manages the web server for handling extension API requests and executing tool calls.
"""

import logging
import json
from aiohttp import web
from aiohttp_cors import setup as setup_cors, ResourceOptions

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ActionLayer:
    def __init__(self, perception_layer, memory_layer, decision_layer):
        """
        Initialize the action layer
        
        Args:
            perception_layer: Instance of PerceptionLayer
            memory_layer: Instance of MemoryLayer
            decision_layer: Instance of DecisionLayer
        """
        self.perception_layer = perception_layer
        self.memory_layer = memory_layer
        self.decision_layer = decision_layer
        self.session = None  # Will hold MCP session
        self.product_info = None  # Will hold product information
        self.current_site = None  # Will hold current site information

    def set_product_info(self, product_info):
        """
        Set or update the product info for analysis
        
        Args:
            product_info: Dictionary containing product information
        """
        self.product_info = product_info
        if "site" in product_info:
            self.current_site = product_info["site"]

    async def handle_product_detection(self, request):
        """
        Handle product detection API requests from the Chrome extension
        
        Args:
            request: aiohttp Request object containing product data
            
        Returns:
            JSON response with analysis results or error message
        """
        try:
            data = await request.json()
            
            # Create a copy of data with redacted review content for logging
            log_data = data.copy()
            if "reviews" in log_data:
                review_count = len(log_data["reviews"]) if log_data["reviews"] else 0
                log_data["reviews"] = f"[{review_count} reviews - content hidden]"
            
            logger.info(f"Received product detection: {log_data}")
            # logger.info(f"Session: {self.session}")
            # Validate required fields
            if "title" not in data:
                logger.error("Missing required field: title")
                return web.json_response({"error": "Missing required field: title"}, status=400)
            
            # Ensure reviews field exists
            if "reviews" not in data or not data["reviews"]:
                data["reviews"] = []
                logger.warning("No reviews provided in request")
                # Add a note to the response that no reviews were provided
                data["review_note"] = "No reviews were provided for analysis. The results are based on limited information."
            
            # Set product info in decision layer and action layer
            self.decision_layer.set_product_info(data)
            self.set_product_info(data)

            # Extract user preferences if present
            user_preferences = None
            if "user_preferences" in data:
                user_preferences = data.get("user_preferences")
                logger.info(f"User preferences received: {user_preferences}")
            
            user_preferences = await self.perception_layer.process_user_preferences(user_preferences)

            # 1. Process product through perception layer
            category = await self.perception_layer.classify_product(data["title"])
            self.decision_layer.set_category(category)  # Set the category in decision layer
            
            # Pass user preferences to craft_initial_prompt
            prompt = await self.perception_layer.craft_initial_prompt(
                data, 
                category,
                user_preferences=user_preferences
            )
            tool_plan = await self.perception_layer.get_tool_invocation_plan(prompt)
            print("Received tool plan from LLM:")
            print(f"Plan with {len(tool_plan.get('tool_calls', []))} tool calls: {[t.get('tool_name', t.get('name', 'unknown')) for t in tool_plan.get('tool_calls', [])]}")
            
            # 2. Execute tool plan and get results
            results = await self.execute_tool_plan(tool_plan)
            
            # 3. Check tool results for reliability
            self_check = await self.check_tool_results(results)
            print(f"Self Check: {self_check}")

            # 4. Get final analysis from decision layer
            final_response = await self.decision_layer.perform_final_reasoning(results, self_check, user_preferences)
            # print(f"Final Response: {final_response}")
            
            # 5. Store analysis in memory layer
            self.memory_layer.store_product_analysis(data, final_response)
            
            # Add layer statuses to response
            final_response["layerStatuses"] = {
                "perception": "complete",
                "memory": "complete",
                "decision": "complete",
                "action": "complete"
            }
            
            # Add the review note if it exists
            if "review_note" in data:
                final_response["review_note"] = data["review_note"]
            
            # Log the response (without sensitive data)
            log_response = final_response.copy()
            if "reviews" in log_response:
                log_response["reviews"] = f"[{len(log_response['reviews'])} reviews - content hidden]"
            logger.info(f"Sending response: {log_response}")
        
            
            # Evaluate preference match
            preference_match = await self.decision_layer.evaluate_preference_match(
                analysis_results=final_response,
                user_preferences=user_preferences
            )
            
            # Include preference match in final results
            final_results = {**final_response, **preference_match}
            
            # Return the results
            return web.json_response(final_results)
            
        except Exception as e:
            logger.error(f"Error processing product detection: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def execute_tool_plan(self, tool_plan):
        """
        Execute the tool invocation plan
        
        Args:
            tool_plan: Dictionary containing the tool invocation plan
            
        Returns:
            Dictionary containing results from all executed tools
        """
        if "error" in tool_plan:
            return {"error": tool_plan["error"]}
        
        results = {}
        logger.info(f"Product Info: {self.product_info}")
        try:
            if "tool_calls" in tool_plan:
                for tool_call in tool_plan["tool_calls"]:
                    # Handle different formats of tool calls
                    tool_name = None
                    tool_input = {}
                    
                    # Extract tool name (could be under 'tool', 'tool_name', or 'function')
                    if "tool" in tool_call:
                        tool_name = tool_call["tool"]
                    elif "tool_name" in tool_call:
                        tool_name = tool_call["tool_name"]
                    elif "function" in tool_call and "name" in tool_call["function"]:
                        tool_name = tool_call["function"]["name"]
                    elif "name" in tool_call:
                        tool_name = tool_call["name"]
                    
                    # Extract tool input (could be under 'input', 'parameters', or 'arguments')
                    if "input" in tool_call:
                        tool_input = tool_call["input"]
                    elif "parameters" in tool_call:
                        tool_input = tool_call["parameters"]
                    elif "arguments" in tool_call:
                        tool_input = tool_call["arguments"]
                    elif "function" in tool_call and "arguments" in tool_call["function"]:
                        tool_input = tool_call["function"]["arguments"]
                    
                    logger.info(f"Executing tool: {tool_name}")
                    
                    # Format the arguments with the required 'input' field
                    # formatted_args = {"input": tool_input}
                    
                    # 1. Classify Product
                    if tool_name in ["classify_product"]:
                        title = tool_input.get("title", self.product_info["title"])
                        result = await self.session.call_tool("classify_product", arguments={
                            "input": {"title": title}
                        })
                        results["classify_product"] = result.content[0].text
                        print(f"Classify Product Results: {results['classify_product']}")
                    
                    # 2. Review Summary Tool
                    elif tool_name in ["review_summary", "review_summary_tool"]:
                        # Map input parameter names
                        product = tool_input.get("product", tool_input.get("product_title", self.product_info["title"]))
                        site = tool_input.get("site", self.current_site)
                        num_reviews = tool_input.get("num_reviews", 1000)
                        
                        # Get reviews from product_data if available
                        reviews = self.product_info.get("reviews", [])
                        # print(f"Reviews: {reviews}")
                        
                        result = await self.session.call_tool("review_summary_tool", arguments={
                            "input": {
                                "product": product,
                                "site": site,
                                "reviews": reviews,
                                "num_reviews": num_reviews
                            }
                        })
                        # Use the result directly instead of trying to parse it as JSON
                        results["review_summary_tool"] = json.loads(result.content[0].text) 
                        print(f"Review Summary Tool Results: {results['review_summary_tool']}")
                    
                    # 3. Calculate Confidence Score
                    elif tool_name in ["calculate_confidence_score"]:
                        # Parse the sentiment data from the review summary tool result
                        try:
                            sentiment_data = results["review_summary_tool"]
                        except json.JSONDecodeError:
                            # If it's not valid JSON, create a default sentiment data
                            sentiment_data = {
                                "overall_sentiment": "Unknown",
                                "sentiment_score": 0,
                                "review_count": 0,
                                "pros": [],
                                "cons": []
                            }
                        
                        result = await self.session.call_tool("calculate_confidence_score", arguments={
                            "input": {
                                "sentiment_data": sentiment_data
                            }
                        })
                        # Use the result directly instead of trying to parse it as JSON
                        results["calculate_confidence_score"] = json.loads(result.content[0].text)  
                        print(f"Calculate Confidence Score Results: {results['calculate_confidence_score']}")

                    # 4. Self Check Tool Results
                    elif tool_name in ["self_check_tool_results"]:
                        # Pass the entire results dictionary directly
                        tools_results = results
                        
                        # print(f"Tools Results format:")
                        # print(f"Tools Results: {tools_results}")
                        result = await self.session.call_tool("self_check_tool_results", arguments={
                            "input": {
                                "tools_results": tools_results
                            }
                        })
                        # Use the result directly instead of trying to parse it as JSON
                        results["self_check_tool_results"] =  json.loads(result.content[0].text)
                        print(f"Self Check Tool Results: {results['self_check_tool_results']}")

                    # 5. Show Reasoning
                    elif tool_name in ["show_reasoning"]:
                        # Create a structured product_data dictionary from the results
                        product_data = {
                            'product_name': self.product_info.get('title', 'Unknown Product'),
                            'sentiment_score': 0,
                            'review_count': 0,
                            'pros': [],
                            'cons': [],
                            'confidence_score': 0,
                            'reliability_score': 0,
                            'reliability_level': 'Unknown'
                        }
                        
                        # Try to parse the review summary tool result
                        try:
                            if isinstance(results.get("review_summary_tool"), str):
                                review_summary = json.loads(results.get("review_summary_tool", "{}"))
                            else:
                                review_summary = results.get("review_summary_tool", {})
                            product_data['sentiment_score'] = review_summary.get('sentiment_score', 0)
                            product_data['review_count'] = review_summary.get('review_count', 0)
                            product_data['pros'] = review_summary.get('pros', [])
                            product_data['cons'] = review_summary.get('cons', [])
                        except json.JSONDecodeError:
                            pass
                        
                        # Try to parse the calculate confidence score result
                        try:
                            if isinstance(results.get("calculate_confidence_score"), str):
                                confidence_score = json.loads(results.get("calculate_confidence_score", "{}"))
                            else:
                                confidence_score = results.get("calculate_confidence_score", {})
                            product_data['confidence_score'] = confidence_score.get('confidence_score', 0)
                        except json.JSONDecodeError:
                            pass
                        
                        # Try to parse the self check tool results
                        try:
                            if isinstance(results.get("self_check_tool_results"), str):
                                self_check = json.loads(results.get("self_check_tool_results", "{}"))
                            else:
                                self_check = results.get("self_check_tool_results", {})
                            product_data['reliability_score'] = self_check.get('reliability_score', 0)
                            product_data['reliability_level'] = self_check.get('reliability_level', 'Unknown')
                        except json.JSONDecodeError:
                            pass
                        
                        result = await self.session.call_tool("show_reasoning", arguments={
                            "input": {
                                "product_data": product_data
                            }
                        })
                        
                        # Use the result directly instead of trying to parse it as JSON
                        results["show_reasoning"] = result.content[0].text
                        print(f"Show Reasoning Results: {results['show_reasoning']}")

                    # 6. Calculate
                    elif tool_name in ["calculate"]:
                        expression = tool_input.get("expression", "")
                        result = await self.session.call_tool("calculate", arguments={
                            "input": {
                                "expression": expression
                            }
                        })
                        # Use the result directly instead of trying to parse it as JSON
                        results["calculate"] = result.content[0].text
                        print(f"Calculate Results: {results['calculate']}")

                    # 7. Verify
                    elif tool_name in ["verify"]:
                        expression = tool_input.get("expression", "")
                        expected = tool_input.get("expected", 0)
                        result = await self.session.call_tool("verify", arguments={
                            "input": {
                                "expression": expression,
                                "expected": float(expected)
                            }
                        })
                        # Use the result directly instead of trying to parse it as JSON
                        results["verify"] = result.content[0].text
                        print(f"Verify Results: {results['verify']}")

                    # 8. Review Consistency Check
                    elif tool_name in ["review_consistency_check"]:
                        # Extract reviews and sentiments from the results dictionary
                        reviews = []
                        sentiments = []
                        
                        # Try to parse the review summary tool result
                        try:
                            review_summary = results.get("review_summary_tool", "{}")
                            reviews = review_summary.get('reviews', [])
                            sentiments = review_summary.get('sentiments', [])
                        except json.JSONDecodeError:
                            pass
                        
                        # Prepare the reviews_data dictionary in the required format
                        reviews_data = {
                            'reviews': reviews,
                            'sentiments': sentiments
                        }
                        
                        # print(f"Extracted reviews_data for consistency check:")
                        # print(f"Reviews count: {len(reviews)}, Sentiments count: {len(sentiments)}")
                        
                        result = await self.session.call_tool("review_consistency_check", arguments={
                            "input": {
                                "reviews_data": reviews_data
                            }
                        })
                        # Use the result directly instead of trying to parse it as JSON
                        results["review_consistency_check"] = result.content[0].text
                        print(f"Review Consistency Check Results:\n {results['review_consistency_check']}")
                    
                    # Backward compatibility for "check_consistency"
                    elif tool_name in ["check_consistency"]:
                        steps = tool_input.get("steps", [])
                        result = await self.session.call_tool("check_consistency", arguments={
                            "input": {
                                "steps": steps
                            }
                        })
                        # Use the result directly instead of trying to parse it as JSON
                        try:
                            results["check_consistency"] = eval(result.content[0].text)
                        except:
                            results["check_consistency"] = result.content[0].text
                        print(f"Check Consistency Results: {results['check_consistency']}")
                    else:
                        logger.warning(f"Unknown tool name: {tool_name}")
                        
            self.tool_results = results
            return results
            
        except Exception as e:
            logger.error(f"Error executing tool plan: {e}")
            return {"error": str(e)}

    async def check_tool_results(self, results):
        """
        Check tool results for reliability
        
        Args:
            results: Dictionary containing tool execution results
            
        Returns:
            Dictionary containing reliability assessment
        """
        try:
            # Format the arguments with the required 'input' field
            formatted_args = {"input": {"tools_results": results}}
            
            result = await self.session.call_tool("self_check_tool_results", 
                                                arguments=formatted_args)
            
            # Check if the result is valid JSON
            try:
                check_results = json.loads(result.content[0].text)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON response from self_check_tool_results: {result.content[0].text}")
                # Create a default response if JSON parsing fails
                check_results = {
                    "reliability_score": 0,
                    "reliability_level": "Low",
                    "issues": ["Invalid response format from self-check tool"],
                    "warnings": ["Could not parse self-check results"],
                    "insights": []
                }
            
            # Create a summary of the results for logging
            check_summary = {
                "reliability_score": check_results.get("reliability_score", 0),
                "reliability_level": check_results.get("reliability_level", "Unknown"),
                "issues_count": len(check_results.get("issues", [])),
                "warnings_count": len(check_results.get("warnings", [])),
                "insights_count": len(check_results.get("insights", []))
            }
            
            logger.info(f"Tool self-check results: {check_summary}")
            return check_summary
            
        except Exception as e:
            logger.error(f"Error checking tool results: {e}")
            return {
                "reliability_score": 0,
                "reliability_level": "Low",
                "issues": [f"Error checking tool results: {str(e)}"],
                "warnings": ["Could not complete self-check"],
                "insights": []
            }

    async def health_check(self, request):
        """
        Health check endpoint to verify server is running
        
        Returns:
            JSON response with OK status
        """
        return web.json_response({"status": "ok"})

    def setup_routes(self, app):
        """
        Setup API routes for the web server
        
        Args:
            app: aiohttp web Application instance
        """
        # Setup API routes
        app.router.add_post('/api/detect-product', self.handle_product_detection)
        app.router.add_get('/', self.health_check)
        
        # Setup CORS to allow requests from the Chrome extension
        cors = setup_cors(app, defaults={
            "*": ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods=["POST", "GET", "OPTIONS"]
            )
        })
        
        # Apply CORS settings to all routes
        for route in list(app.router.routes()):
            cors.add(route) 