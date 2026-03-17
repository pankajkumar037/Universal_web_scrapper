"""CLI test — verify the Crew pipeline works outside Streamlit."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import nest_asyncio
nest_asyncio.apply()

from agents.crew import run_crew_pipeline


def cli_callback(step, data=None):
    data = data or {}
    parts = [f"[{step}]"]
    for k, v in data.items():
        parts.append(f"{k}={v}")
    print("  ".join(parts))


def main():
    url = "https://www.naukri.com/python-developer-jobs"
    description = "job listings with title, company, experience, salary, location, skills"
    num_pages = 1

    if len(sys.argv) > 1:
        url = sys.argv[1]
    if len(sys.argv) > 2:
        description = sys.argv[2]

    print(f"URL: {url}")
    print(f"Description: {description}")
    print(f"Pages: {num_pages}")
    print("-" * 60)

    result = run_crew_pipeline(
        url=url,
        description=description,
        num_pages=num_pages,
        callback=cli_callback,
    )

    print("-" * 60)
    print(f"Records extracted: {len(result.get('records', []))}")
    print(f"Schema: {result.get('schema', {})}")
    print(f"Crawl info: {result.get('crawl_info', [])}")

    if result.get("records"):
        print(f"\nFirst record:")
        for k, v in result["records"][0].items():
            print(f"  {k}: {v}")
    else:
        print("\nNo records extracted.")


if __name__ == "__main__":
    main()
