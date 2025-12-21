import os
import asyncio
import base64
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
# from langchain_openai import ChatOpenAI
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use import Agent, Browser

from .utils import logger
from .models import ScrapeContext

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

    async def run_task(self, task_description: str, city: str = "Unknown") -> ScrapeContext:
        """
        Run a scraping task using Browser-Use.

        Args:
            task_description: The natural language description of the task.
            city: The city name for context tracking.

        Returns:
            ScrapeContext with full history for handoff to Claude Code.
        """
        logger.info(f"Starting Browser-Use agent task for {city}...")

        agent = Agent(
            task=task_description,
            llm=self.llm,
            browser=self.browser,
            max_actions_per_step=1,
        )

        try:
            history = await agent.run(max_steps=30)

            # Extract screenshots and save to disk
            screenshot_paths = []
            screenshots_dir = Path("data/screenshots") / city.lower().replace(" ", "_")
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            raw_screenshots = history.screenshots(n_last=3) if hasattr(history, 'screenshots') else []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # One timestamp per scrape run
            for i, screenshot in enumerate(raw_screenshots):
                if screenshot:
                    try:
                        filepath = screenshots_dir / f"{timestamp}_{i+1}.png"
                        img_data = base64.b64decode(screenshot)
                        filepath.write_bytes(img_data)
                        screenshot_paths.append(str(filepath))
                    except Exception as e:
                        logger.warning(f"Failed to save screenshot {i+1}: {e}")

            # Extract rich context from history
            context = ScrapeContext(
                city=city,
                final_result=history.final_result() if hasattr(history, 'final_result') else None,
                is_done=history.is_done() if hasattr(history, 'is_done') else False,
                is_successful=history.is_successful() if hasattr(history, 'is_successful') else None,
                errors=history.errors() if hasattr(history, 'errors') else [],
                urls=history.urls() if hasattr(history, 'urls') else [],
                actions=history.action_names() if hasattr(history, 'action_names') else [],
                screenshots=raw_screenshots,  # Keep base64 for JSONL
                screenshot_paths=screenshot_paths,  # Add paths
                task_description=task_description,
            )

            return context

        except Exception as e:
            logger.error(f"Error running Browser-Use task: {e}")
            # Return context even on exception
            return ScrapeContext(
                city=city,
                final_result=None,
                is_done=False,
                is_successful=False,
                errors=[str(e)],
                urls=[],
                actions=[],
                screenshots=[],
                task_description=task_description,
            )
        finally:
            await self.browser.stop()

    async def close(self):
        await self.browser.stop()
