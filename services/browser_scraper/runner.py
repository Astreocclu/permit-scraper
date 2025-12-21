import asyncio
import json
import argparse
from typing import Dict, Optional, Any, List
import datetime
import os

from .agent import PermitScraperAgent
from .permit_tasks import get_task_for_city
from .utils import log_scrape_attempt, estimate_cost, logger
from .models import ScrapeContext

class PermitScraperRunner:
    def __init__(self):
        self.agent = None

    def _create_agent(self) -> PermitScraperAgent:
        """Factory method for creating agent (allows mocking in tests)."""
        return PermitScraperAgent()

    async def scrape_permit(self, city: str, address: str = "", permit_type: str = "Building", mode: str = "single", start_date: str = "", end_date: str = "") -> Dict[str, Any]:
        """
        Main entry point to scrape a permit.

        Returns dict with:
            success: bool
            data: parsed JSON or raw output
            error: error message if any
            context: ScrapeContext dict for review/handoff
        """
        success = False
        error_msg = None
        result_data = {}
        context: Optional[ScrapeContext] = None

        try:
            # Get task description
            mgo_email = os.getenv("MGO_EMAIL", "")
            mgo_password = os.getenv("MGO_PASSWORD", "")

            task_desc = get_task_for_city(
                city=city,
                address=address,
                permit_type=permit_type,
                mgo_email=mgo_email,
                mgo_password=mgo_password,
                mode=mode,
                start_date=start_date,
                end_date=end_date
            )

            # Initialize agent using factory method
            self.agent = self._create_agent()

            # Execute and get rich context
            context = await self.agent.run_task(task_desc, city=city)

            # Try to parse JSON from final_result
            if context.final_result and context.is_successful:
                clean_result = context.final_result.strip()
                # Strip markdown code blocks
                if clean_result.startswith("```json"):
                    clean_result = clean_result.replace("```json", "").replace("```", "")
                elif clean_result.startswith("```"):
                    clean_result = clean_result.replace("```", "")

                try:
                    result_data = json.loads(clean_result)
                    success = True
                except json.JSONDecodeError:
                    error_msg = "Failed to parse JSON response"
                    result_data = {"raw_output": context.final_result}
            else:
                error_msg = "Scrape incomplete or unsuccessful"
                result_data = {"raw_output": context.final_result}

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Scrape failed: {e}")
        finally:
            if self.agent:
                await self.agent.close()

            log_scrape_attempt(
                city,
                address if mode == 'single' else f"{start_date}-{end_date}",
                success,
                0,  # tokens placeholder
                error_msg
            )

        return {
            "success": success,
            "data": result_data,
            "error": error_msg,
            "context": context.to_dict() if context else None
        }


class BatchRunner:
    def __init__(self, concurrency: int = 5):
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        self.results = []

    async def run_batch(self, cities: List[str], address: str = "", permit_type: str = "Building", mode: str = "single", start_date: str = "", end_date: str = ""):
        """
        Run scraping for multiple cities concurrently.
        """
        logger.info(f"Starting batch run for {len(cities)} cities. Mode: {mode}")
        
        tasks = []
        for city in cities:
            tasks.append(self._scrape_safe(city, address, permit_type, mode, start_date, end_date))
            
        self.results = await asyncio.gather(*tasks)
        
        # Save results
        await self._save_results()
        return self.results

    async def _scrape_safe(self, city: str, address: str, permit_type: str, mode: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Wrapper to run scrape with semaphore and exception handling.
        """
        async with self.semaphore:
            logger.info(f"Scraping city: {city}")
            runner = PermitScraperRunner()
            result_payload = {}
            try:
                # Add a small random delay to avoid thundering herd if needed, 
                # but semaphore handles the bulk of it.
                result = await runner.scrape_permit(city, address, permit_type, mode, start_date, end_date)
                result_payload = {
                    "city": city,
                    "status": "success" if result["success"] else "failed",
                    "data": result.get("data"),
                    "error": result.get("error"),
                    "timestamp": datetime.datetime.now().isoformat()
                }
            except Exception as e:
                logger.error(f"Critical failure for {city}: {e}")
                result_payload = {
                    "city": city,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.datetime.now().isoformat()
                }
            
            # Incremental Save
            self._append_result(result_payload)
            return result_payload

    def _append_result(self, result: Dict[str, Any]):
        """
        Append a single result to the incremental JSON file.
        """
        filename = "data/incremental_batch_results.json"
        
        # Lock handling (simplified for single process, but good practice)
        # We'll read, append, write. 
        # CAUTION: In high concurrency this is racy, but with low concurrency (e.g. 1-2) it's okay for now.
        # A better approach is appending to a JSONL file (one line per record).
        
        jsonl_filename = "data/incremental_batch_results.jsonl"
        with open(jsonl_filename, "a") as f:
            f.write(json.dumps(result) + "\n")
            
        logger.info(f"Saved result for {result['city']} to {jsonl_filename}")

async def run_cli():
    parser = argparse.ArgumentParser(description="Run Browser-Use Permit Scraper")
    parser.add_argument("--city", help="City to scrape (single mode)")
    parser.add_argument("--address", help="Address to search (required for single mode)")
    parser.add_argument("--type", default="Building", help="Permit type")
    parser.add_argument("--batch", action="store_true", help="Run in batch mode for all cities")
    parser.add_argument("--limit", type=int, help="Limit number of cities for testing")
    parser.add_argument("--cities_file", default="data/target_cities.json", help="Path to cities JSON list")
    
    # Bulk mode args
    parser.add_argument("--mode", default="single", choices=["single", "bulk"], help="Scraping mode")
    parser.add_argument("--days", type=int, help="Number of previous days to scrape (for bulk mode)")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD) for bulk mode")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD) for bulk mode")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent city scrapers (default: 5)")
    
    args = parser.parse_args()
    
    # Calculate dates if days provided
    start_date = args.start_date
    end_date = args.end_date
    
    if args.mode == "bulk":
        if args.days:
            end = datetime.datetime.now()
            start = end - datetime.timedelta(days=args.days)
            end_date = end.strftime("%m/%d/%Y")
            start_date = start.strftime("%m/%d/%Y")
        elif not (start_date and end_date):
            # Default to 30 days if nothing specified
            end = datetime.datetime.now()
            start = end - datetime.timedelta(days=30)
            end_date = end.strftime("%m/%d/%Y")
            start_date = start.strftime("%m/%d/%Y")
    
    if args.batch:
        if not args.cities_file or not os.path.exists(args.cities_file):
            print(f"Error: Cities file not found at {args.cities_file}")
            return

        with open(args.cities_file, 'r') as f:
            all_cities = json.load(f)
            
        if args.limit:
            all_cities = all_cities[:args.limit]
            
        batch_runner = BatchRunner(concurrency=args.concurrency)
        results = await batch_runner.run_batch(
            cities=all_cities, 
            address=args.address if args.address else "", 
            permit_type=args.type,
            mode=args.mode,
            start_date=start_date,
            end_date=end_date
        )
        print(f"Batch run complete. Processed {len(results)} cities.")
        
    elif args.city:
        runner = PermitScraperRunner()
        result = await runner.scrape_permit(
            city=args.city, 
            address=args.address if args.address else "", 
            permit_type=args.type,
            mode=args.mode,
            start_date=start_date,
            end_date=end_date
        )
        print(json.dumps(result, indent=2))
    else:
        print("Error: Must specify --city or --batch")


if __name__ == "__main__":
    asyncio.run(run_cli())
