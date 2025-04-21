"""
Smart Purchase Advisor - Perception Layer

This module handles the initial perception and analysis of product data using LLM.
It processes raw product data and performs initial classification and analysis.
"""

import json
import logging
from google import genai
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerceptionLayer:
    def __init__(self, client):
        """
        Initialize the perception layer
        
        Args:
            client: Initialized Gemini client
        """
        self.client = client
        self.session = None  # Will hold MCP session

    async def generate_with_timeout(self, prompt, timeout=20):
        """
        Generate content using Gemini with a timeout to prevent hanging
        
        Args:
            prompt: Text prompt to send to the model
            timeout: Maximum time to wait in seconds (default: 20)
            
        Returns:
            Response from Gemini or None if timeout or error occurs
        """
        try:
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    lambda: self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt
                    )
                ),
                timeout=timeout
            )
            return response
        except asyncio.TimeoutError:
            logger.error("LLM request timed out")
            return None
        except Exception as e:
            logger.error(f"Error in LLM request: {e}")
            return None

    async def classify_product(self, title):
        """
        Classify the product using the MCP classify_product tool
        
        Args:
            title: Product title string
            
        Returns:
            String containing the product category
        """
        logger.info(f"Classifying product: {title}")
        result = await self.session.call_tool("classify_product", arguments={"input": {"title": title}})
        category = result.content[0].text
        logger.info(f"Product category detected: {category}")
        return category

    async def process_user_preferences(self, user_preferences):
        """
        Process and validate user preferences
        
        Args:
            user_preferences: Dictionary containing user preferences
            
        Returns:
            Dictionary containing processed and validated preferences
        """
        logger.info("Processing user preferences")
        
        # Default preferences structure
        default_preferences = {
            "price_range": {"min": 0, "max": float('inf')},
            "brand_preferences": [],
            "feature_priorities": [],
            "avoid_features": [],
            "review_threshold": 10,
            "sentiment_threshold": 0.5,
            "confidence_threshold": 70
        }
        
        try:
            # Merge provided preferences with defaults
            processed_preferences = default_preferences.copy()
            
            if user_preferences:
                # Update price range if provided
                if "price_range" in user_preferences:
                    price_range = user_preferences["price_range"]
                    if isinstance(price_range, dict):
                        if "min" in price_range:
                            processed_preferences["price_range"]["min"] = float(price_range["min"])
                        if "max" in price_range:
                            processed_preferences["price_range"]["max"] = float(price_range["max"])
                
                # Update brand preferences if provided
                if "brand_preferences" in user_preferences and isinstance(user_preferences["brand_preferences"], list):
                    processed_preferences["brand_preferences"] = user_preferences["brand_preferences"]
                
                # Update feature priorities if provided
                if "feature_priorities" in user_preferences and isinstance(user_preferences["feature_priorities"], list):
                    processed_preferences["feature_priorities"] = user_preferences["feature_priorities"]
                
                # Update features to avoid if provided
                if "avoid_features" in user_preferences and isinstance(user_preferences["avoid_features"], list):
                    processed_preferences["avoid_features"] = user_preferences["avoid_features"]
                
                # Update thresholds if provided
                if "review_threshold" in user_preferences:
                    processed_preferences["review_threshold"] = int(user_preferences["review_threshold"])
                if "sentiment_threshold" in user_preferences:
                    processed_preferences["sentiment_threshold"] = float(user_preferences["sentiment_threshold"])
                if "confidence_threshold" in user_preferences:
                    processed_preferences["confidence_threshold"] = float(user_preferences["confidence_threshold"])
            
            logger.info(f"Processed user preferences: {processed_preferences}")
            return processed_preferences
            
        except Exception as e:
            logger.error(f"Error processing user preferences: {e}")
            return default_preferences

    async def craft_initial_prompt(self, product_data, category, user_preferences=None):
        """
        Craft the initial prompt for the LLM to create a tool invocation plan
        
        Args:
            product_data: Dictionary containing product info
            category: Product category from classify_product
            user_preferences: Optional dictionary containing user preferences
            
        Returns:
            String containing the crafted prompt
        """
        # Process user preferences if provided
        processed_preferences = await self.process_user_preferences(user_preferences)
        
        # Define the example JSON outside the f-string to avoid nesting issues
        example_json = '''
        {
          "tool_calls": [
            {
              "tool_name": "review_summary_tool",
              "parameters": {
                "product": "Samsung Galaxy S23 Ultra",
                "site": "amazon.com",
                "num_reviews": 100000
              }
            },
            {
              "tool_name": "calculate_confidence_score",
              "parameters": {
                "sentiment_data": {"sentiment_score": 0.75, "review_count": 10, "pros": ["Great camera", "Fast performance"], "cons": ["Battery life", "Price"]}
              }
            },
            {
              "tool_name": "self_check_tool_results",
              "parameters": {
                "tools_results": [{"review_summary_tool": {"result": "..."}}, {"calculate_confidence_score": {"result": "..."}}]
              }
            },
            {
                "tool_name": "show_reasoning",
                "parameters": {
                    "product_data": {
                        "product_name": "Samsung Galaxy S23 Ultra",
                        "review_count": 10,
                        "sentiment_score": 0.75,
                        "pros": ["Great camera", "Fast performance"],
                        "cons": ["Battery life", "Price"],
                        "confidence_score": 85,
                        "reliability_score": 80,
                        "reliability_level": "High"
                    }
                }
            },
            {
                "tool_name": "review_consistency_check",
                "parameters": {
                    "reviews": ["Good product", "Bad product", "Great product", "Terrible product"],
                    "overall_sentiment": [0,0,-0.04,0.05,0.6,1,-0.5]
                }
            }
          ]
        }
        '''
        
        # Main system prompt with tool descriptions and instructions
        prompt = f"""
        You are a Product Review Analyzer. Your task is to analyze product reviews and provide 
        a sentiment analysis with a confidence score to help shoppers make informed decisions.
        
        You will create a tool invocation plan to:
        1. Classify the product category
        2. Summarize reviews using sentiment analysis
        3. Calculate a confidence score based on the review sentiment
        4. Provide detailed reasoning and consistency checks
        
        You have access to these tools:
        - classify_product(title: str) - Classifies product category based on title using semantic similarity
        - review_summary_tool(product: str, site: str = None, reviews: list = None, num_reviews: int = 100000) - Analyzes product reviews and returns sentiment analysis
        - calculate_confidence_score(sentiment_data: dict) - Calculates a confidence score based on sentiment data
        - self_check_tool_results(tools_results: list) - Self-check sentinel reliability and highlight potential issues
        - show_reasoning(product_data: dict) - Show detailed explanation of sentiment analysis and confidence score calculation
        - calculate(expression: str) - Calculate sentiment metrics or confidence score components
        - verify(expression: str, expected: float) - Verify sentiment metrics or confidence score calculations
        - review_consistency_check(reviews_data: dict) - Check consistency of review sentiments and identify potential biases
        
        Example tool invocation plan:
        ```json
{example_json}
        ```
        
        The confidence score should be calculated based on:
        - The overall sentiment polarity (positive, neutral, negative)
        - The consistency of reviews (are they all similar or varied?)
        - The quantity of reviews analyzed
        - The presence of specific, detailed pros and cons
        
        For each step, you will specify the tool to use and the input parameters.
        You must verify each tool's success and provide fallbacks if needed.
        
        Your response must be in JSON format with a structured "tool_calls" array that includes the EXACT function names as shown above.
        
        TASK: Create a tool invocation plan to analyze reviews and calculate confidence.
        """
        
        # Create JSON product data separately to avoid nested f-string
        product_json = json.dumps({
            "title": product_data["title"],
            "site": product_data.get("site", "Unknown"),
            "category": category,
            "price": product_data.get("price", "Unknown"),
            "url": product_data.get("url", "Unknown")
        })
        
        # Append the product JSON to the prompt
        prompt += f"PRODUCT: {product_json}"
        
        # Append user preferences if available
        if processed_preferences:
            preferences_json = json.dumps(processed_preferences)
            prompt += f"\nUSER PREFERENCES: {preferences_json}"
        
        return prompt

    async def get_tool_invocation_plan(self, prompt):
        """
        Get the tool invocation plan from the LLM
        
        Args:
            prompt: String containing the prompt for the LLM
            
        Returns:
            Dictionary containing the parsed tool invocation plan
        """
        response = await self.generate_with_timeout(prompt)
        
        if not response or not response.text:
            logger.error("Failed to get response from LLM")
            return {"error": "Failed to get response from LLM"}
        
        try:
            # Extract JSON from potential markdown code blocks
            text = response.text
            if "```json" in text and "```" in text:
                # Extract content between ```json and the last ```
                json_text = text.split("```json", 1)[1].split("```", 1)[0].strip()
            elif "```" in text:
                # Extract content between first ``` and last ```
                json_text = text.split("```", 1)[1].split("```", 1)[0].strip()
            else:
                json_text = text
                
            result = json.loads(json_text)
            logger.info("Successfully received tool invocation plan from LLM")
            return result
        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response as JSON: {response.text}")
            return {"error": "Failed to parse LLM response"} 