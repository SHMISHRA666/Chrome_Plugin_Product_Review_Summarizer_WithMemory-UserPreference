"""
Smart Purchase Advisor - Memory Layer

This module handles storing and managing product analysis history and results.
It maintains a persistent memory of analyzed products and their results.
"""

import json
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MemoryLayer:
    def __init__(self, storage_dir="memory"):
        """
        Initialize the memory layer
        
        Args:
            storage_dir: Directory to store memory files
        """
        self.storage_dir = storage_dir
        self.ensure_storage_dir()
        self.preferences_file = os.path.join(storage_dir, "user_preferences.json")
        
    def ensure_storage_dir(self):
        """Ensure the storage directory exists"""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            
    def _get_product_filename(self, product_id):
        """
        Generate filename for product data
        
        Args:
            product_id: Unique identifier for the product
            
        Returns:
            String containing the filename
        """
        # Sanitize the product_id to create a valid filename
        # Replace invalid characters and truncate if too long
        sanitized_id = "".join(c for c in product_id if c.isalnum() or c in [' ', '_', '-'])
        sanitized_id = sanitized_id.replace(' ', '_')
        
        # Truncate if too long (Windows has a 260 character path limit)
        if len(sanitized_id) > 150:
            # Keep the first 100 chars and the timestamp part (which should be at the end)
            timestamp_part = sanitized_id[-20:] if len(sanitized_id) >= 20 else ""
            sanitized_id = sanitized_id[:100] + "_" + timestamp_part
            
        return os.path.join(self.storage_dir, f"{sanitized_id}.json")
        
    def store_product_analysis(self, product_data, analysis_results, user_preferences=None):
        """
        Store product analysis results
        
        Args:
            product_data: Original product data
            analysis_results: Results from the analysis
            user_preferences: Optional user preferences used for analysis
        """
        try:
            # Ensure storage directory exists
            self.ensure_storage_dir()
            
            # Create a unique product ID from title and timestamp
            # Use a shorter version of the title to avoid filename issues
            title = product_data['title']
            short_title = title[:50] + "..." if len(title) > 50 else title
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            product_id = f"{short_title}_{timestamp}"
            
            filename = self._get_product_filename(product_id)
            
            # Combine product data and analysis results
            memory_entry = {
                "product_data": product_data,
                "analysis_results": analysis_results,
                "timestamp": datetime.now().isoformat(),
                "product_id": product_id
            }
            
            # Add user preferences if provided
            if user_preferences:
                memory_entry["user_preferences"] = user_preferences
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(memory_entry, f, indent=2)
                
            logger.info(f"Stored analysis for product: {product_id}")
            return product_id
            
        except Exception as e:
            logger.error(f"Error storing product analysis: {e}")
            return None
            
    def retrieve_product_analysis(self, product_id):
        """
        Retrieve stored product analysis
        
        Args:
            product_id: Unique identifier for the product
            
        Returns:
            Dictionary containing the stored analysis or None if not found
        """
        try:
            filename = self._get_product_filename(product_id)
            if not os.path.exists(filename):
                logger.warning(f"No stored analysis found for product: {product_id}")
                return None
                
            with open(filename, 'r') as f:
                memory_entry = json.load(f)
                
            logger.info(f"Retrieved analysis for product: {product_id}")
            return memory_entry
            
        except Exception as e:
            logger.error(f"Error retrieving product analysis: {e}")
            return None
            
    def get_recent_analyses(self, limit=10):
        """
        Get most recent product analyses
        
        Args:
            limit: Maximum number of analyses to return
            
        Returns:
            List of recent memory entries
        """
        try:
            # Get all JSON files in storage directory
            files = [f for f in os.listdir(self.storage_dir) if f.endswith('.json') and f != "user_preferences.json"]
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: os.path.getmtime(os.path.join(self.storage_dir, x)), 
                      reverse=True)
            
            # Get the most recent files up to the limit
            recent_files = files[:limit]
            
            # Load the analyses
            recent_analyses = []
            for filename in recent_files:
                filepath = os.path.join(self.storage_dir, filename)
                with open(filepath, 'r') as f:
                    memory_entry = json.load(f)
                    recent_analyses.append(memory_entry)
                    
            logger.info(f"Retrieved {len(recent_analyses)} recent analyses")
            return recent_analyses
            
        except Exception as e:
            logger.error(f"Error retrieving recent analyses: {e}")
            return []
            
    def search_analyses(self, query):
        """
        Search through stored analyses
        
        Args:
            query: Search query string
            
        Returns:
            List of matching memory entries
        """
        try:
            matches = []
            files = [f for f in os.listdir(self.storage_dir) if f.endswith('.json') and f != "user_preferences.json"]
            
            for filename in files:
                filepath = os.path.join(self.storage_dir, filename)
                with open(filepath, 'r') as f:
                    memory_entry = json.load(f)
                    
                    # Search in product title and analysis results
                    product_title = memory_entry['product_data'].get('title', '').lower()
                    if query.lower() in product_title:
                        matches.append(memory_entry)
                        continue
                        
                    # Search in analysis results
                    analysis = memory_entry.get('analysis_results', {})
                    if any(query.lower() in str(v).lower() for v in analysis.values()):
                        matches.append(memory_entry)
                        
            logger.info(f"Found {len(matches)} matches for query: {query}")
            return matches
            
        except Exception as e:
            logger.error(f"Error searching analyses: {e}")
            return []

    def store_user_preferences(self, user_preferences):
        """
        Store user preferences
        
        Args:
            user_preferences: Dictionary containing user preferences
            
        Returns:
            Boolean indicating success
        """
        try:
            with open(self.preferences_file, 'w') as f:
                json.dump(user_preferences, f, indent=2)
            logger.info("Stored user preferences")
            return True
        except Exception as e:
            logger.error(f"Error storing user preferences: {e}")
            return False

    def get_user_preferences(self):
        """
        Retrieve stored user preferences
        
        Returns:
            Dictionary containing user preferences or None if not found
        """
        try:
            if not os.path.exists(self.preferences_file):
                logger.info("No stored user preferences found")
                return None
                
            with open(self.preferences_file, 'r') as f:
                preferences = json.load(f)
                
            logger.info("Retrieved user preferences")
            return preferences
            
        except Exception as e:
            logger.error(f"Error retrieving user preferences: {e}")
            return None 