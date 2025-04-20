from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Union, Any
from enum import Enum

# Common type for tool responses
class TextContent(BaseModel):
    type: str = "text"
    text: str

# Models for classify_product
class ClassifyProductInput(BaseModel):
    title: str = Field(..., description="Product title to classify")

class ClassifyProductOutput(BaseModel):
    category: str

# Models for review_summary_tool
class ReviewSummaryInput(BaseModel):
    product: str = Field(..., description="Product name or identifier")
    site: str = Field(None, description="Source site of the reviews")
    reviews: List[str] = Field(None, description="List of review texts")
    num_reviews: int = Field(100000, description="Maximum number of reviews to analyze")

class ReviewSummaryOutput(BaseModel):
    reviews: List[str]
    overall_sentiment: str
    sentiment_score: float
    sentiments: List[float]
    pros: List[str]
    cons: List[str]
    review_count: int
    source: str

# Models for self_check_tool_results
class ToolsResultsInput(BaseModel):
    tools_results: Dict = Field(None, description="Results from review summary and calculate confidence score tool")

class SelfCheckOutput(BaseModel):
    reliability_score: float
    reliability_level: str
    review_count: int
    sentiment_score: float
    issues: List[str]
    warnings: List[str]
    insights: List[str]

# Models for show_reasoning
class ProductData(BaseModel):
    product_data: Dict = Field(None, description="Product data")

class ReasoningOutput(BaseModel):
    product_name: str
    review_count: int
    sentiment: Dict[str, Any]
    confidence: Dict[str, Any]
    reliability: Dict[str, Any]
    pros_count: int
    cons_count: int
    recommendation: str

# Models for calculate and verify
class CalculateInput(BaseModel):
    expression: str = Field(..., description="Mathematical expression to evaluate")

class CalculateOutput(BaseModel):
    result: str

class VerifyInput(BaseModel):
    expression: str = Field(..., description="Expression to verify")
    expected: float = Field(..., description="Expected result")

class VerifyOutput(BaseModel):
    result: str

# Models for review_consistency_check
class ReviewsData(BaseModel):
    reviews_data: Dict = Field(None, description="Reviews data")

class ConsistencyCheckOutput(BaseModel):
    review_count: int
    avg_sentiment: float
    std_deviation: float
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    bias_level: str
    consistency_level: str
    insights: List[str]

# Models for calculate_confidence_score
class ConfidenceScoreComponents(BaseModel):
    sentiment_data: Dict = Field(None, description="Sentiment data")

class ConfidenceScoreOutput(BaseModel):
    confidence_score: float
    explanation: str
    confidence_level: str
    components: Dict[str, float]

# Enums for common values
class SentimentLevel(str, Enum):
    POSITIVE = "Positive"
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"

class ConfidenceLevel(str, Enum):
    VERY_HIGH = "Very High"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"
    VERY_LOW = "Very Low"

class BiasLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

class ConsistencyLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"