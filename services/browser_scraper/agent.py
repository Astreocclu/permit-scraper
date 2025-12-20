import os
import asyncio
from typing import Optional, Dict, Any, List
# from langchain_openai import ChatOpenAI
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use import Agent, Browser
 
from .utils import logger

class PermitScraperAgent:
    def __init__(self, headless: bool = True):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY is not set.")
        
        self.headless = headless or os.getenv("BROWSER_USE_HEADLESS", "true").lower() == "true"
        
        # Configure DeepSeek LLM
        self.llm = ChatOpenAI(
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_key=self.api_key,
            temperature=0.0, # Deterministic for scraping
            dont_force_structured_output=True, # DeepSeek doesn't support response_format='json_schema' yet
            add_schema_to_system_prompt=True,
        )
        
        # Initialize Browser
        self.browser = Browser(
            headless=self.headless,
            disable_security=True,
        )

    async def run_task(self, task_description: str) -> str:
        """
        Run a scraping task using Browser-Use.
        
        Args:
            task_description: The natural language description of the task.
            
        Returns:
            The result string (JSON or text) from the agent.
        """
        logger.info(f"Starting Browser-Use agent task...")
        
        agent = Agent(
            task=task_description,
            llm=self.llm,
            browser=self.browser,
            max_actions_per_step=1, # Default
        )
        
        try:
            # Enforce max_steps here (default is 100)
            history = await agent.run(max_steps=30)
            
            # The result is typically the last action's output or a final extracted string.
            # Browser-Use API might return history object, need to extract final result.
            # Assuming history.final_result() or similar based on library version.
            # If standard API, run() returns history. checking docs or assuming standard behavior.
            # If history object, we usually want the last message or result.
            
            # For now, assuming history object has a mechanism to get the final answer.
            # If run() returns the result directly (some versions do), we handle that.
            
            # Just returning the history for now as per updated library understanding,
            # usually there is a method to get the final result.
            result = history.final_result() if hasattr(history, 'final_result') else str(history)
            
            return result
            
        except Exception as e:
            logger.error(f"Error running Browser-Use task: {e}")
            raise
        finally:
            # Clean up browser if needed, though agent might handle it.
            # self.browser.close() # Browser instance is persistent in this class?
            # Ideally we close it when the service stops.
            # For single-run tasks, maybe we should close it.
            await self.browser.stop()

    async def close(self):
        await self.browser.stop()
