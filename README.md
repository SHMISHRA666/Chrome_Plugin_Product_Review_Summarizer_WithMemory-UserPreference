# Smart Purchase Advisor with Memory

A sophisticated AI-powered system that helps users make informed purchase decisions by analyzing product reviews and maintaining contextual memory of user preferences and past interactions.

## Overview

This project implements a multi-layer cognitive architecture for intelligent product review analysis and purchase recommendations. It combines natural language processing, memory management, and decision-making capabilities to provide personalized shopping assistance.

## Features

- **Product Review Analysis**: Summarizes and analyzes product reviews from various sources
- **Memory Management**: Maintains context and user preferences across sessions
- **Intelligent Decision Making**: Provides personalized purchase recommendations
- **Chrome Extension**: Browser integration for seamless shopping assistance
- **Real-time Processing**: Asynchronous processing of reviews and recommendations

## Architecture

The system is built on a layered cognitive architecture:

- **Perception Layer**: Handles data collection and initial processing
- **Memory Layer**: Manages user preferences and historical data
- **Decision Layer**: Processes information and makes recommendations
- **Action Layer**: Executes actions and provides user feedback

## Prerequisites

- Python 3.13 or higher
- Google API key for Generative AI
- Chrome browser (for extension functionality)

## Installation

1. Clone the repository:
```bash
git clone [repository-url]
cd smart-purchase-advisor
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file with your API keys and configuration:
```
GOOGLE_API_KEY=your_api_key_here
```

## Usage

1. Start the main server:
```bash
python Product_Review_Summariser_main.py
```

2. Install the Chrome extension from the `chrome_extension` directory

3. The system will now provide purchase recommendations as you browse products online

## Project Structure

- `Product_Review_Summariser_main.py`: Main application entry point
- `perception_layer.py`: Data collection and processing
- `memory_layer.py`: User preference and context management
- `decision_layer.py`: Recommendation engine
- `action_layer.py`: Action execution and feedback
- `mcp_server.py`: Message Control Protocol server
- `chrome_extension/`: Browser extension implementation
- `memory/`: Persistent storage for user data

## Dependencies

- aiohttp: Asynchronous HTTP client/server
- google-generativeai: Google's Generative AI API
- sentence-transformers: Text embedding and processing
- rich: Terminal formatting and output
- fastmcp: Message Control Protocol implementation

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Limitations
1. This is not the best version of the tool
2. Currently only works with Amazon product pages
3. Limited to processing reviews visible on the current page
4. Navigation to the review page can retrieve more reviews, but not all at once
5. Web scraping functionality could be improved and optimized
6. Review analysis is limited by the quality and quantity of available reviews
7. The system currently stores memory data per product rather than per user.