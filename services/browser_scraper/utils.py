import logging
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Setup logger
logger = logging.getLogger("browser_scraper")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def log_scrape_attempt(city: str, address: str, success: bool, tokens: int = 0, error: str = None):
    """
    Log usage and outcome of a scrape attempt.
    In a real system, this would write to a database or monitoring service.
    """
    status = "SUCCESS" if success else "FAILURE"
    msg = f"City: {city}, Address: {address}, Status: {status}, Tokens: {tokens}"
    if error:
        msg += f", Error: {error}"
    
    logger.info(msg)
    
    # Simple file-based logging for cost tracking (as a placeholder for DB)
    usage_file = "browser_usage.log"
    with open(usage_file, "a") as f:
        timestamp = datetime.now().isoformat()
        f.write(f"{timestamp},{city},{address},{status},{tokens},{error or ''}\n")

def estimate_cost(tokens: int, model: str = "deepseek-chat") -> float:
    """
    Estimate cost based on token usage. 
    DeepSeek pricing is roughly $0.14/1M input tokens (cache miss) and $0.28/1M output tokens.
    Assuming mostly input tokens for scraping contexts.
    """
    # Simplified estimation
    rate_per_1m = 0.14 # Base approximation
    cost = (tokens / 1_000_000) * rate_per_1m
    return cost
