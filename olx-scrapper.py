import time
import csv
import json
import random
import logging
import requests
import argparse
from datetime import datetime
from bs4 import BeautifulSoup
import re
import os
import traceback

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("olx_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger()

class OlxScraper:
    def __init__(self, search_query, max_pages=1, use_selenium=False, proxy=None, country="in"):
        self.search_query = search_query
        self.max_pages = max_pages
        self.use_selenium = use_selenium
        self.proxy = proxy
        self.country = country  # Country code (in for India, ae for UAE, etc.)
        self.results = []
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:105.0) Gecko/20100101 Firefox/125.0"
        ]
        
        # Create directory for debug files
        os.makedirs("debug", exist_ok=True)
    
    def get_random_user_agent(self):
        """Return a random user agent from the list"""
        return random.choice(self.user_agents)
    
    def scrape_with_requests(self):
        """Scrape OLX using the requests library (no browser automation)"""
        # Format the URL - replace spaces with hyphens for OLX search
        formatted_query = self.search_query.replace(" ", "-")
        base_url = f"https://www.olx.{self.country}/items/q-{formatted_query}"
        
        for page in range(1, self.max_pages + 1):
            url = f"{base_url}?page={page}" if page > 1 else base_url
            logger.info(f"Loading page {page} with requests: {url}")
            
            headers = {
                "User-Agent": self.get_random_user_agent(),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }
            
            proxy_dict = None
            if self.proxy:
                proxy_dict = {
                    "http": self.proxy,
                    "https": self.proxy
                }
            
            # Add a random delay between requests
            time.sleep(2 + random.random() * 3)
            
            try:
                response = requests.get(url, headers=headers, proxies=proxy_dict, timeout=20)
                
                # Save the response for debugging
                debug_file = f"debug/olx_requests_page_{page}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                    
                logger.info(f"Page {page} response status: {response.status_code}")
                
                if response.status_code == 200:
                    # Parse the response
                    page_results = self.parse_html(response.text, page)
                    self.results.extend(page_results)
                else:
                    logger.error(f"Failed to retrieve page {page}: Status code {response.status_code}")
            
            except Exception as e:
                logger.error(f"Error retrieving page {page}: {e}")
                traceback.print_exc()
    
    def scrape_with_selenium(self):
        """Scrape OLX using Selenium WebDriver"""
        try:
            # Only import Selenium when needed
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, WebDriverException
            
            chrome_options = Options()
            # Comment out headless mode for debugging
            # chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument(f"user-agent={self.get_random_user_agent()}")
            
            # Set up proxy if provided
            if self.proxy:
                chrome_options.add_argument(f'--proxy-server={self.proxy}')
            
            # Try to use the installed Chrome WebDriver
            try:
                service = Service()
                driver = webdriver.Chrome(service=service, options=chrome_options)
                logger.info("Successfully initialized Chrome WebDriver with system driver")
            except WebDriverException:
                # Fall back to ChromeDriverManager
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Successfully initialized Chrome WebDriver with ChromeDriverManager")
                except Exception as e:
                    logger.error(f"Failed to initialize Chrome WebDriver: {e}")
                    raise
            
            # Format the URL
            formatted_query = self.search_query.replace(" ", "-")
            base_url = f"https://www.olx.{self.country}/items/q-{formatted_query}"
            
            for page in range(1, self.max_pages + 1):
                url = f"{base_url}?page={page}" if page > 1 else base_url
                logger.info(f"Loading page {page} with Selenium: {url}")
                
                # Add a random delay between pages
                if page > 1:
                    time.sleep(3 + random.random() * 2)
                
                # Load the page with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        driver.get(url)
                        
                        # Wait for page to load (try multiple selectors)
                        try:
                            WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-aut-id='itemBox']"))
                            )
                        except TimeoutException:
                            # Try alternative wait conditions
                            WebDriverWait(driver, 15).until(
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                        
                        # Add a small delay for JavaScript to fully load
                        time.sleep(3)
                        
                        logger.info(f"Page {page} loaded successfully")
                        
                        # Save the page source for debugging
                        html = driver.page_source
                        debug_file = f"debug/olx_selenium_page_{page}.html"
                        with open(debug_file, "w", encoding="utf-8") as f:
                            f.write(html)
                        
                        # Parse the page
                        page_results = self.parse_html(html, page)
                        self.results.extend(page_results)
                        break
                        
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Error on page {page}, retrying ({attempt+1}/{max_retries}): {e}")
                            time.sleep(5)  # Wait before retrying
                        else:
                            logger.error(f"Failed to load page {page} after {max_retries} attempts: {e}")
                            # Save the current page source for debugging
                            try:
                                with open(f"debug/olx_selenium_error_page_{page}.html", "w", encoding="utf-8") as f:
                                    f.write(driver.page_source)
                            except:
                                pass
                            break
            
            driver.quit()
            logger.info("WebDriver closed")
            
        except Exception as e:
            logger.error(f"Error during Selenium scraping: {e}")
            traceback.print_exc()
    
    def try_api_approach(self):
        """Try to access OLX API endpoints directly"""
        # OLX sometimes has API endpoints that can be accessed directly
        formatted_query = self.search_query.replace(" ", "+")
        
        # Different OLX domains might have different API structures
        # This is a common pattern, but might need adjustments
        base_api_url = f"https://www.olx.{self.country}/api/relevance/search?query={formatted_query}"
        
        headers = {
            "User-Agent": self.get_random_user_agent(),
            "Accept": "application/json",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        try:
            response = requests.get(base_api_url, headers=headers, timeout=15)
            
            # Save the API response for analysis
            with open("debug/olx_api_response.json", "w", encoding="utf-8") as f:
                f.write(response.text)
                
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info("Successfully retrieved data from API")
                    
                    # Parse API response - structure will depend on OLX's API
                    # This is a placeholder - adapt based on actual API response
                    if "data" in data and isinstance(data["data"], list):
                        for item in data["data"]:
                            listing = {}
                            listing["title"] = item.get("title", "N/A")
                            listing["price"] = item.get("price", {}).get("value", "N/A")
                            listing["location"] = item.get("location", {}).get("label", "N/A")
                            listing["date_posted"] = item.get("created_at", "N/A")
                            listing["url"] = item.get("url", "N/A")
                            self.results.append(listing)
                    
                except ValueError:
                    logger.warning("API response is not valid JSON")
            else:
                logger.warning(f"API request failed with status code: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error accessing API: {e}")
    
    def parse_html(self, html, page_num):
        """Parse HTML to extract listing information"""
        page_results = []
        
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Try multiple selectors for listings
            listings = []
            
            # Strategy 1: Look for itemBox data attribute (common in newer OLX designs)
            listings = soup.select("[data-aut-id='itemBox']")
            
            # Strategy 2: Look for list items with specific class patterns
            if not listings:
                listings = soup.find_all("li", class_=re.compile(r"_.*item.*"))
            
            # Strategy 3: Look for cards/divs with listing content
            if not listings:
                listings = soup.select(".EIR5N")  # Example class name, adjust based on inspection
            
            # Strategy 4: Generic listing pattern (fallback)
            if not listings:
                listings = soup.select("div[class*='listing']")
                if not listings:
                    listings = soup.select("div[class*='item']")
            
            if not listings:
                logger.warning(f"No listings found on page {page_num} using any selector method")
                # Check for possible API blocking or CAPTCHA
                if "captcha" in html.lower() or "robot" in html.lower():
                    logger.warning("Possible CAPTCHA or anti-bot measures detected")
                elif "access denied" in html.lower() or "blocked" in html.lower():
                    logger.warning("Access appears to be blocked or denied")
                
                return page_results
            
            logger.info(f"Found {len(listings)} listings on page {page_num}")
            
            # Process each listing
            for listing in listings:
                listing_data = {}
                
                # Extract title - try multiple selectors
                title = None
                title_selectors = [
                    "[data-aut-id='itemTitle']",
                    "span[class*='title']",
                    "h2",
                    ".title",
                    "[class*='title']"
                ]
                
                for selector in title_selectors:
                    title_tag = listing.select_one(selector)
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        break
                
                listing_data["title"] = title if title else "N/A"
                
                # Extract price - try multiple selectors
                price = None
                price_selectors = [
                    "[data-aut-id='itemPrice']",
                    "span[class*='price']",
                    ".price",
                    "[class*='price']"
                ]
                
                for selector in price_selectors:
                    price_tag = listing.select_one(selector)
                    if price_tag:
                        price = price_tag.get_text(strip=True)
                        break
                
                listing_data["price"] = price if price else "N/A"
                
                # Extract location - try multiple selectors
                location = None
                location_selectors = [
                    "[data-aut-id='item-location']",
                    "span[class*='location']",
                    ".location",
                    "[class*='location']"
                ]
                
                for selector in location_selectors:
                    location_tag = listing.select_one(selector)
                    if location_tag:
                        location = location_tag.get_text(strip=True)
                        break
                
                listing_data["location"] = location if location else "N/A"
                
                # Extract date posted - try multiple selectors
                date = None
                date_selectors = [
                    "[data-aut-id='itemCreationDate']",
                    "span[class*='date']",
                    ".date",
                    "[class*='date']",
                    "[class*='time']"
                ]
                
                for selector in date_selectors:
                    date_tag = listing.select_one(selector)
                    if date_tag:
                        date = date_tag.get_text(strip=True)
                        break
                
                listing_data["date_posted"] = date if date else "N/A"
                
                # Extract URL
                url = None
                link_tag = listing.find("a")
                if link_tag and 'href' in link_tag.attrs:
                    href = link_tag['href']
                    # Ensure absolute URL
                    if href.startswith('/'):
                        url = f"https://www.olx.{self.country}{href}"
                    elif href.startswith('http'):
                        url = href
                    else:
                        url = f"https://www.olx.{self.country}/{href}"
                
                listing_data["url"] = url if url else "N/A"
                
                # Only add if we have meaningful data
                if listing_data["title"] != "N/A" or listing_data["price"] != "N/A":
                    page_results.append(listing_data)
            
        except Exception as e:
            logger.error(f"Error parsing HTML for page {page_num}: {e}")
            traceback.print_exc()
        
        return page_results
    
    def scrape(self):
        """Main scraping method that tries different approaches"""
        logger.info(f"Starting OLX scraper for '{self.search_query}' in {self.country}")
        
        # First try the requests approach (simpler, less resource-intensive)
        self.scrape_with_requests()
        
        # If we got results, we can stop here
        if self.results:
            logger.info(f"Successfully scraped {len(self.results)} listings using requests approach")
            return self.results
        
        # If no results from requests, try the API approach
        logger.info("No results from requests approach, trying API approach")
        self.try_api_approach()
        
        # If we got results from API, we can stop here
        if self.results:
            logger.info(f"Successfully scraped {len(self.results)} listings using API approach")
            return self.results
        
        # If still no results and Selenium is enabled, try Selenium
        if self.use_selenium:
            logger.info("No results from requests or API, trying Selenium approach")
            self.scrape_with_selenium()
            
            if self.results:
                logger.info(f"Successfully scraped {len(self.results)} listings using Selenium approach")
            else:
                logger.warning("No results from any approach")
        else:
            logger.info("Selenium approach skipped (disabled)")
            
        return self.results
    
    def save_results(self):
        """Save scraping results to both TXT and CSV formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"olx_{self.search_query.replace(' ', '_')}_{timestamp}"
        
        # Save to TXT
        txt_filename = f"{base_filename}.txt"
        with open(txt_filename, "w", encoding="utf-8") as file:
            file.write(f"OLX Search Results for '{self.search_query}'\n")
            file.write("=" * 60 + "\n\n")
            
            if not self.results:
                file.write("No listings found.\n")
            else:
                for i, listing in enumerate(self.results, 1):
                    file.write(f"Listing #{i}\n")
                    file.write(f"Title: {listing['title']}\n")
                    file.write(f"Price: {listing['price']}\n")
                    file.write(f"Location: {listing['location']}\n")
                    file.write(f"Date Posted: {listing['date_posted']}\n")
                    file.write(f"URL: {listing['url']}\n")
                    file.write("-" * 60 + "\n")
        
        # Save to CSV
        csv_filename = f"{base_filename}.csv"
        with open(csv_filename, "w", encoding="utf-8", newline="") as file:
            if not self.results:
                file.write("No listings found.\n")
            else:
                fieldnames = ["title", "price", "location", "date_posted", "url"]
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                for listing in self.results:
                    writer.writerow(listing)
        
        # Save raw JSON for programmatic access
        json_filename = f"{base_filename}.json"
        with open(json_filename, "w", encoding="utf-8") as file:
            json.dump(self.results, file, indent=2)
        
        return txt_filename, csv_filename, json_filename

def main():
    """Main function to run the scraper"""
    parser = argparse.ArgumentParser(description="OLX Scraper Tool")
    parser.add_argument("--query", type=str, default="car cover", help="Search query")
    parser.add_argument("--pages", type=int, default=3, help="Maximum number of pages to scrape")
    parser.add_argument("--selenium", action="store_true", help="Use Selenium if other methods fail")
    parser.add_argument("--proxy", type=str, help="Proxy to use (format: http://host:port)")
    parser.add_argument("--country", type=str, default="in", help="Country code for OLX domain (e.g., 'in' for India)")
    
    args = parser.parse_args()
    
    scraper = OlxScraper(
        search_query=args.query,
        max_pages=args.pages,
        use_selenium=args.selenium,
        proxy=args.proxy,
        country=args.country
    )
    
    results = scraper.scrape()
    
    if results:
        logger.info(f"Successfully scraped {len(results)} listings")
        txt_file, csv_file, json_file = scraper.save_results()
        print(f"\nResults saved to:\n- {txt_file}\n- {csv_file}\n- {json_file}")
        print(f"\nTotal listings found: {len(results)}")
    else:
        logger.warning("No results found")
        print("\nNo listings were found. Check the debug directory and log file for details.")
        print("\nTry running with --selenium flag for browser automation approach")

if __name__ == "__main__":
    main()