"""
Smart Purchase Advisor - Decision Making Layer

This module handles the final reasoning and confidence assessment using LLM.
It processes the results from other layers to make final decisions about product recommendations.
"""

import json
import logging
from google import genai
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DecisionLayer:
    def __init__(self, client, product_info=None):
        """
        Initialize the decision making layer
        
        Args:
            client: Initialized Gemini client
            product_info: Optional initial product info, can be set later
        """
        self.client = client
        self.session = None  # Will hold MCP session
        self.product_info = product_info
        self.category = None  # Initialize category as None

    def set_product_info(self, product_info):
        """
        Set or update the product info for analysis
        
        Args:
            product_info: Dictionary containing product information
        """
        self.product_info = product_info

    def set_category(self, category):
        """
        Set the product category
        
        Args:
            category: String containing the product category
        """
        self.category = category

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

    async def perform_final_reasoning(self, results, self_check):
        """
        Perform final reasoning with the LLM using tool results
        
        Args:
            results: Dictionary containing all tool execution results
            self_check: Dictionary containing reliability assessment
            
        Returns:
            Dictionary containing the final structured analysis
        """
        if not self.category:
            logger.warning("Category not set in decision layer")
            self.category = "Unknown"  # Provide a default value

        # Create examples outside of f-string to avoid nesting issues
        examples = """
EXAMPLE OUTPUTS FROM TOOLS:

1. classify_product:
   Input: {"title": "Samsung Galaxy S23 Ultra"}
   Output: "smartphone"

2. review_summary_tool:
   Input: {"product": "Samsung Galaxy S23 Ultra", "site": "amazon.com","reviews": ["Great phone!", "Love the camera"], "num_reviews": 100000}
   Output: {
     "reviews": ["Great phone!", "Love the camera"],
     "overall_sentiment": "Positive",
     "sentiment_score": 0.75,
     "sentiments": [0.8, 0.9],
     "pros": ["Great camera", "Fast performance", "Beautiful display"],
     "cons": ["Battery life could be better", "Expensive"],
     "review_count": 10,
     "source": "amazon.com"
   }

3. calculate_confidence_score:
   Input: {"reviews": ["Great phone!", "Love the camera"],
     "overall_sentiment": "Positive",
     "sentiment_score": 0.75,
     "sentiments": [0.8, 0.9],
     "pros": ["Great camera", "Fast performance", "Beautiful display"],
     "cons": ["Battery life could be better", "Expensive"],
     "review_count": 10,
     "source": "amazon.com"}
   Output: {
     "confidence_score": 85,
     "explanation": "Confidence score of 85% calculated based on...",
     "confidence_level": "High Confidence: Reviews indicate this is likely a good product",
     "components": {
       "sentiment_component": 62.5,
       "review_count_component": 15.0,
       "specificity_component": 5.0,
       "balance_component": 2.5
     }
   }

4. self_check_tool_results:
   Input: {"tools_results": [{"review_summary_tool": {...}}, {"calculate_confidence_score": {...}}]}
   Output: {
     "reliability_score": 80,
     "reliability_level": "High",
     "review_count": 10,
     "sentiment_score": 0.75,
     "issues": ["No issues found"],
     "warnings": ["Limited sample size (10 reviews) may affect confidence"],
     "insights": ["Good sample size (10 reviews) for analysis"]
   }

5. show_reasoning:
   Input: {"product_data": 
   {"product_name": "Samsung Galaxy S23 Ultra", 
   	"sentiment_score": 0.3
    "review_count": 23,
    "pros": ["Great camera", "Fast performance", "Beautiful display"],
     "cons": ["Battery life could be better", "Expensive"],
    "confidence_score": 60,
    "reliability_score": 50,
    "reliability_level":"Low"}}
   Output: {
            "product_name": "Samsung Galaxy S23 Ultra",
            "review_count": 23,
            "sentiment": {
                "score": 0.3,
                "label": "Positive",
                "explanation": "The product has strongly positive sentiment based on user reviews."
            },
            "confidence": {
                "score": 55,
                "label": "High"
                "explanation": "Confidence score: 70/100 (High)"
            },
            "reliability": {
                "score": 50,
                "level": Low
            },
            "pros_count": 5,
            "cons_count": 6,
            "recommendation": "Recommendation: Product is recommended with high confidence."
        }

6. review_consistency_check:
   Input: {"reviews_data": {"reviews": ["Great phone!", "Love the camera"], "sentiments": [0.8, 0.9]}}
   Output: {
     "review_count": 10,
     "avg_sentiment": 0.75,
     "std_deviation": 0.3,
     "positive_ratio": 0.7,
     "negative_ratio": 0.2,
     "neutral_ratio": 0.1,
     "bias_level": "Medium",
     "consistency_level": "High",
     "insights": ["Sample size is adequate for reliable sentiment analysis"]
   }
"""

        # Main prompt for final reasoning
        prompt = f"""
        You are a Product Review Analyzer. You have analyzed the reviews for a product 
        and now need to provide a structured summary with sentiment analysis and confidence score.
        
        The following tools were used in the analysis:
        - classify_product(title: str) - Classifies product category based on title using semantic similarity
        - review_summary_tool(product: str, site: str = None, reviews: list = None, num_reviews: int = 100000) - Analyzes product reviews and returns sentiment analysis
        - calculate_confidence_score(sentiment_data: dict) - Calculates a confidence score based on sentiment data
        - self_check_tool_results(tools_results: dict) - Self-check sentinel reliability and highlight potential issues
        - show_reasoning(product_data: dict) - Show detailed explanation of sentiment analysis and confidence score calculation
        - calculate(expression: str) - Calculate sentiment metrics or confidence score components
        - verify(expression: str, expected: float) - Verify sentiment metrics or confidence score calculations
        - review_consistency_check(reviews_data: dict) - Check consistency of review sentiments and identify potential biases
        
{examples}

        Create a concise response including:
        1. Product category based on title
        2. Review sentiment summary with pros and cons
        3. Confidence score (on a scale of 0-100%) with explanation
        4. Key factors that influenced the confidence score
        5. Confidence level interpretation
        
        The confidence score considers:
        - Overall sentiment polarity (positive reviews increase confidence)
        - Consistency of sentiments across reviews
        - Quantity and quality of specific pros and cons mentioned
        - Number of reviews analyzed
        - Balance between pros and cons (having both is more reliable)
        
        If confidence score components are provided, include them to show
        how the score was calculated.
        
        Output must be in JSON format suitable for display in a Chrome extension sidebar with these fields:
        - title: product title
        - overall_sentiment: overall sentiment assessment (positive, negative, or neutral)
        - sentiment_score: numerical sentiment score
        - confidence_score: numerical confidence score (0-100)
        - confidence_level: text interpretation of the confidence score
        - pros: array of key pros from reviews
        - cons: array of key cons from reviews
        - confidence_explanation: explanation of how confidence was calculated
        - confidence_components: breakdown of score components if available (sentiment_component, review_count_component, specificity_component, balance_component)
        - review_count: number of reviews analyzed
        - reliability_score: score from self-check (0-100)
        - reliability_level: level from self-check (Low, Medium, High)
        - issues: array of critical issues found during self-check
        - warnings: array of warnings found during self-check
        - insights: array of insights found during self-check
        
        EXAMPLE FINAL OUTPUT:
        {{
          "title": "Samsung Galaxy S23 Ultra",
          "overall_sentiment": "Positive",
          "sentiment_score": 0.75,
          "confidence_score": 85,
          "confidence_level": "High Confidence",
          "pros": ["Great camera", "Fast performance", "Beautiful display"],
          "cons": ["Battery life could be better", "Expensive"],
          "confidence_explanation": "Confidence score of 85% calculated based on sentiment (62.5 points), review count (15.0 points), specificity (5.0 points), and balance (2.5 points)",
          "confidence_components": {{
            "sentiment_component": 62.5,
            "review_count_component": 15.0,
            "specificity_component": 5.0,
            "balance_component": 2.5
          }},
          "review_count": 10,
          "reliability_score": 80,
          "reliability_level": "High",
          "issues": [],
          "warnings": ["Limited sample size (10 reviews) may affect confidence"],
          "insights": ["Good sample size (10 reviews) for analysis"]
        }}
        
        TASK: Generate final sentiment analysis and confidence assessment
        """
        
        # Add product info and results to prompt without logging full content
        prompt += f"""
        PRODUCT INFO: {json.dumps(self.product_info)}
        CATEGORY: {self.category}
        TOOL RESULTS: {json.dumps(results)}
        SELF CHECK: {json.dumps(self_check)}
        """
        
        # Get the final analysis from the LLM
        response = await self.generate_with_timeout(prompt)
        
        if not response or not response.text:
            logger.error("Failed to get final response from LLM")
            return {"error": "Failed to get final response from LLM"}
        
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
            logger.info("Successfully received final analysis from LLM")
            
            return result
        
        except json.JSONDecodeError:
            logger.error(f"Failed to parse final LLM response as JSON: {response.text}")
            
            # Fallback: Try to create a response directly from the tool results
            confidence_result = results.get("calculate_confidence_score", {})
            review_result = results.get("review_summary_tool", {})
            self_check_result = results.get("self_check_tool_results", {})
            
            # Construct fallback response with available data
            return {
                "overall_sentiment": review_result.get("overall_sentiment", "Unknown"),
                "sentiment_score": review_result.get("sentiment_score", 0),
                "confidence_score": confidence_result.get("confidence_score", 0),
                "confidence_level": confidence_result.get("confidence_level", "Unknown confidence"),
                "pros": review_result.get("pros", ["No pros found"]),
                "cons": review_result.get("cons", ["No cons found"]),
                "confidence_explanation": confidence_result.get("explanation", "Could not calculate confidence score"),
                "confidence_components": confidence_result.get("components", {}),
                "review_count": review_result.get("review_count", 0),
                "reliability_score": self_check_result.get("reliability_score", 0),
                "reliability_level": self_check_result.get("reliability_level", "Unknown"),
                "issues": self_check_result.get("issues", []),
                "warnings": self_check_result.get("warnings", []),
                "insights": self_check_result.get("insights", []),
                "error": "Failed to generate structured analysis"
            } 