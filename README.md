
# OLX Scraper

A Python tool for scraping listings from OLX websites based on a search query.

## Features
- Scrapes OLX listings using `requests`, optional Selenium, or API-based approaches.
- Extracts listing details such as:
  - **Title**
  - **Price**
  - **Location**
  - **Date Posted**
  - **URL**
- Saves results in **TXT**, **CSV**, and **JSON** formats.
- Supports multiple countries (e.g., `in` for India, `ae` for UAE).
- Fully configurable via command-line arguments.

## Requirements
- Python **3.6+**
- Install dependencies:
  ```bash
  pip install requests beautifulsoup4 selenium webdriver-manager

## Usage

```bash
python olx_scraper.py --query "car cover" --pages 3 --country in
```

## Output

* Results are saved as:

  ```
  olx_<query>_<timestamp>.{txt,csv,json}
  ```
* Debug files are saved in the `debug/` directory.
* Logs are saved in the `olx_scraper.log` file.

