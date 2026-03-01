import os
import asyncio
import base64
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from browser_use.llm.openai.chat import ChatOpenAI
from browser_use.llm.anthropic.chat import ChatAnthropic
from browser_use import Agent, Browser

from .utils import logger
from .models import ScrapeContext

# Model configurations with pricing (per 1M tokens)
MODEL_CONFIGS = {
    "deepseek": {
        "provider": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "input_cost": 0.14,  # $/1M tokens
        "output_cost": 0.28,
        "supports_structured": False,
    },
    "sonnet": {
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
        "input_cost": 3.00,
        "output_cost": 15.00,
        "supports_structured": True,
    },
    "haiku": {
        "provider": "anthropic",
        "model": "claude-3-5-haiku-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
        "input_cost": 0.80,
        "output_cost": 4.00,
        "supports_structured": True,
    },
    "opus": {
        "provider": "anthropic",
        "model": "claude-opus-4-20250514",
        "api_key_env": "ANTHROPIC_API_KEY",
        "input_cost": 15.00,
        "output_cost": 75.00,
        "supports_structured": True,
    },
}

ModelType = Literal["deepseek", "sonnet", "haiku", "opus"]

# Find Chromium path
def find_chromium() -> Optional[str]:
    """Find Playwright Chromium executable."""
    paths = [
        Path.home() / ".cache/ms-playwright/chromium-1200/chrome-linux64/chrome",
        Path.home() / ".cache/ms-playwright/chromium-1148/chrome-linux64/chrome",
        Path("/usr/bin/chromium-browser"),
        Path("/usr/bin/chromium"),
        Path("/usr/bin/google-chrome"),
    ]
    for p in paths:
        if p.exists():
            return str(p)
    return None


class PermitScraperAgent:
    def __init__(self, headless: bool = True, model: ModelType = "deepseek", cdp_port: int = 9222, max_steps: int = 30):
        self.model_name = model
        self.max_steps = max_steps
        config = MODEL_CONFIGS[model]

        self.api_key = os.getenv(config["api_key_env"])
        if not self.api_key:
            raise ValueError(f"{config['api_key_env']} is not set.")

        self.headless = headless or os.getenv("BROWSER_USE_HEADLESS", "true").lower() == "true"
        self.input_cost = config["input_cost"]
        self.output_cost = config["output_cost"]
        self.cdp_port = cdp_port

        # Track usage for cost calculation
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.start_time = None
        self._browser_process = None

        # Configure LLM based on provider
        if config["provider"] == "anthropic":
            self.llm = ChatAnthropic(
                model=config["model"],
                api_key=self.api_key,
                temperature=0.0,
            )
        else:
            # OpenAI-compatible (DeepSeek)
            self.llm = ChatOpenAI(
                base_url=config["base_url"],
                model=config["model"],
                api_key=self.api_key,
                temperature=0.0,
                dont_force_structured_output=not config["supports_structured"],
                add_schema_to_system_prompt=True,
            )

        # Start browser with CDP and connect
        self._start_browser_cdp()

        # Connect browser-use to our CDP instance
        self.browser = Browser(
            cdp_url=f"http://127.0.0.1:{self.cdp_port}",
        )

    def _start_browser_cdp(self):
        """Start Chromium with CDP debugging port."""
        chromium_path = find_chromium()
        if not chromium_path:
            raise RuntimeError("Could not find Chromium browser")

        args = [
            chromium_path,
            f"--remote-debugging-port={self.cdp_port}",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
        ]

        if self.headless:
            args.append("--headless=new")

        logger.info(f"Starting Chromium with CDP on port {self.cdp_port}...")
        self._browser_process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Wait for CDP to be ready
        for _ in range(30):
            try:
                resp = requests.get(f"http://127.0.0.1:{self.cdp_port}/json/version", timeout=1)
                if resp.ok:
                    logger.info("CDP ready!")
                    return
            except:
                pass
            time.sleep(0.2)

        raise RuntimeError(f"CDP not ready after 6 seconds on port {self.cdp_port}")

    def _stop_browser(self):
        """Stop the browser process."""
        if self._browser_process:
            self._browser_process.terminate()
            try:
                self._browser_process.wait(timeout=5)
            except:
                self._browser_process.kill()
            self._browser_process = None

    def get_cost_estimate(self) -> Dict[str, float]:
        """Calculate estimated cost based on token usage."""
        input_cost = (self.total_input_tokens / 1_000_000) * self.input_cost
        output_cost = (self.total_output_tokens / 1_000_000) * self.output_cost
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": input_cost + output_cost,
        }

    async def run_task(self, task_description: str, city: str = "Unknown") -> ScrapeContext:
        """
        Run a scraping task using Browser-Use.

        Args:
            task_description: The natural language description of the task.
            city: The city name for context tracking.

        Returns:
            ScrapeContext with full history for handoff to Claude Code.
        """
        logger.info(f"Starting Browser-Use agent task for {city} using {self.model_name}...")
        self.start_time = time.time()

        agent = Agent(
            task=task_description,
            llm=self.llm,
            browser=self.browser,
            max_actions_per_step=1,
        )

        try:
            history = await agent.run(max_steps=self.max_steps)
            elapsed = time.time() - self.start_time

            # Extract screenshots and save to disk
            screenshot_paths = []
            screenshots_dir = Path("data/screenshots") / city.lower().replace(" ", "_")
            screenshots_dir.mkdir(parents=True, exist_ok=True)

            raw_screenshots = history.screenshots(n_last=3) if hasattr(history, 'screenshots') else []
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for i, screenshot in enumerate(raw_screenshots):
                if screenshot:
                    try:
                        filepath = screenshots_dir / f"{timestamp}_{i+1}.png"
                        img_data = base64.b64decode(screenshot)
                        filepath.write_bytes(img_data)
                        screenshot_paths.append(str(filepath))
                    except Exception as e:
                        logger.warning(f"Failed to save screenshot {i+1}: {e}")

            # Capture extracted content files (saved by Browser-Use extract action)
            # Browser-Use saves to /tmp/browser_use_agent_<uuid>/browseruse_agent_data/
            extracted_content = []
            extracted_files = []
            import glob
            import os

            # Search in multiple locations where Browser-Use might save files
            search_patterns = [
                "extracted_content_*.md",  # Current directory
                "/tmp/browser_use_agent_*/browseruse_agent_data/extracted_content_*.md",  # Browser-Use temp
            ]

            for pattern in search_patterns:
                for extract_file in sorted(glob.glob(pattern)):
                    if extract_file not in extracted_files:  # Avoid duplicates
                        try:
                            with open(extract_file, 'r') as f:
                                content = f.read()
                                extracted_content.append(content)
                                extracted_files.append(extract_file)
                                logger.info(f"Captured extracted content from: {extract_file}")
                        except Exception as e:
                            logger.warning(f"Failed to read {extract_file}: {e}")

            # Extract rich context from history
            context = ScrapeContext(
                city=city,
                final_result=history.final_result() if hasattr(history, 'final_result') else None,
                is_done=history.is_done() if hasattr(history, 'is_done') else False,
                is_successful=history.is_successful() if hasattr(history, 'is_successful') else None,
                errors=history.errors() if hasattr(history, 'errors') else [],
                urls=history.urls() if hasattr(history, 'urls') else [],
                actions=history.action_names() if hasattr(history, 'action_names') else [],
                screenshots=raw_screenshots,
                screenshot_paths=screenshot_paths,
                task_description=task_description,
                extracted_content=extracted_content,
                extracted_files=extracted_files,
            )

            # Add benchmark metadata
            context.model = self.model_name
            context.elapsed_seconds = elapsed
            context.cost_estimate = self.get_cost_estimate()

            return context

        except Exception as e:
            logger.error(f"Error running Browser-Use task: {e}")
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
            self._stop_browser()

    async def close(self):
        await self.browser.stop()
        self._stop_browser()
