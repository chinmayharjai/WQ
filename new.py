import os
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
import geckodriver_autoinstaller
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import queue
import re

# Configuration
USERNAME = "zoho.exfactorguidebiz@gmail.com"
PASSWORD = "PaSSWORD@123"
BASE_URL = "https://platform.worldquantbrain.com"
LOGIN_URL = f"{BASE_URL}/sign-in"
START_URLS = [
    f"{BASE_URL}/learn",
    f"{BASE_URL}/data",
    f"{BASE_URL}/community"
]

# Create output directory
output_dir = "scraped_content"
os.makedirs(output_dir, exist_ok=True)

# Keep track of visited URLs
visited_urls = set()

def human_like_delay():
    """Add random delays to mimic human behavior"""
    time.sleep(random.uniform(2, 5))

def setup_driver():
    """Set up and return a Firefox WebDriver with anti-detection measures"""
    try:
        # Set up Firefox options
        firefox_options = Options()
        # Keep browser visible
        # firefox_options.add_argument("--headless")  # Commented out to make browser visible
        
        # Add anti-detection measures
        firefox_options.set_preference("dom.webdriver.enabled", False)
        firefox_options.set_preference("useAutomationExtension", False)
        firefox_options.set_preference("general.useragent.override", "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0")
        
        # Create the service with webdriver-manager
        service = Service(GeckoDriverManager().install())
        
        # Create the driver
        driver = webdriver.Firefox(service=service, options=firefox_options)
        
        # Set window size to match laptop screen
        driver.set_window_size(1366, 768)
        
        return driver
        
    except Exception as e:
        print(f"Error setting up Firefox driver: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Make sure Firefox is installed on your system")
        print("2. Try running 'pip install --upgrade webdriver-manager'")
        print("3. Try manually downloading geckodriver from: https://github.com/mozilla/geckodriver/releases")
        print("4. Make sure Firefox and geckodriver versions are compatible")
        raise

def handle_unexpected_page(driver, expected_url, current_url):
    """Handle unexpected page redirects with user intervention"""
    print("\nREACHED UNEXPECTED PAGE")
    print(f"Expected: {expected_url}")
    print(f"Current:  {current_url}")
    print("\nOptions:")
    print("1. Wait for manual intervention (you can interact with the page)")
    print("2. Scrape this page anyway and continue")
    print("3. Skip this page")
    
    choice = input("\nEnter your choice (1/2/3): ").strip()
    
    if choice == '1':
        print("\nWaiting for your manual intervention...")
        input("Press Enter when ready to continue...")
        return True
    elif choice == '2':
        print("\nProceeding to scrape current page...")
        return True
    else:
        print("\nSkipping this page...")
        return False

def login(driver):
    """Handle the login process with human-like behavior"""
    print("Starting login process...")
    
    try:
        # Navigate to login page
        driver.get(LOGIN_URL)
        print("Waiting for page to load...")
        time.sleep(5)  # Wait for page to fully load
        
        print("Please handle the cookie popup manually if it appears...")
        input("Press Enter after accepting/rejecting cookies...")
        
        # Check if we're on the expected login page
        if not driver.current_url.endswith('/sign-in'):
            print("\nNot on the expected login page.")
            if not handle_unexpected_page(driver, LOGIN_URL, driver.current_url):
                return False
        
        # Wait for the login form and fields to be present
        print("Looking for email and password fields...")
        
        # Wait for and find email field (trying different possible attributes)
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='email'], input[id='email']"))
        )
        
        # Find password field
        password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        
        # Clear fields first
        email_field.clear()
        password_field.clear()
        
        # Type credentials with human-like delays
        print("Entering email...")
        for char in USERNAME:
            email_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
            
        human_like_delay()
        
        print("Entering password...")
        for char in PASSWORD:
            password_field.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
            
        human_like_delay()
        
        # Find and click the login button
        print("Looking for login button...")
        login_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        print("Clicking login button...")
        login_button.click()
        
        # Wait for login to complete
        print("Waiting for login to complete...")
        time.sleep(5)
        
        # Check if login was successful
        current_url = driver.current_url
        if "dashboard" in current_url.lower() or "learn" in current_url.lower():
            print("Login successful!")
            return True
        else:
            print("Reached unexpected page after login.")
            return handle_unexpected_page(driver, "dashboard or learn page", current_url)
            
    except Exception as e:
        print(f"Login failed: {str(e)}")
        print("Current URL:", driver.current_url)
        # Offer manual intervention on login error
        return handle_unexpected_page(driver, LOGIN_URL, driver.current_url)

def wait_for_page_load(driver, timeout=30):
    """Wait for page to fully load including dynamic content"""
    try:
        # Wait for the initial page load
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script('return document.readyState') == 'complete'
        )
        
        # Wait for any loading indicators to disappear (adjust selectors based on actual page)
        loading_indicators = [
            "//div[contains(@class, 'loading')]",
            "//div[contains(@class, 'spinner')]",
            "//div[contains(@class, 'loader')]"
        ]
        
        for indicator in loading_indicators:
            try:
                WebDriverWait(driver, 5).until_not(
                    EC.presence_of_element_located((By.XPATH, indicator))
                )
            except:
                pass
        
        # Additional delay for dynamic content
        time.sleep(3)
        
        # Scroll through the page to trigger lazy loading
        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            # Scroll down in smaller steps
            for i in range(3):
                driver.execute_script(f"window.scrollTo(0, {(i+1) * last_height/3});")
                time.sleep(1)
            
            # Calculate new scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            
        # Scroll back to top
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
    except Exception as e:
        print(f"Warning: Page load wait encountered an error: {str(e)}")

def is_relevant_url(url):
    """Check if URL is relevant for scraping"""
    relevant_patterns = [
        r'/learn/',
        r'/data/',
        r'/community/',
        r'/course/',
        r'/lesson/',
        r'/tutorial/',
        r'/article/',
        r'/discussion/',
        r'/project/'
    ]
    return any(re.search(pattern, url) for pattern in relevant_patterns)

def extract_links(soup, base_url):
    """Extract all relevant internal links from the page"""
    links = set()
    for anchor in soup.find_all('a', href=True):
        href = anchor['href']
        if href.startswith('/') or href.startswith(base_url):
            full_url = urljoin(base_url, href)
            if is_relevant_url(full_url) and full_url not in visited_urls:
                links.add(full_url)
    return list(links)

def save_page_content(url, content):
    """Save the page content to a file with proper naming"""
    try:
        # Create subdirectory based on URL structure
        url_path = url.replace(BASE_URL, '').strip('/')
        if not url_path:
            url_path = 'home'
        
        # Replace invalid filename characters
        safe_path = re.sub(r'[<>:"/\\|?*]', '_', url_path)
        
        # Create subdirectories if needed
        file_dir = os.path.join(output_dir, os.path.dirname(safe_path))
        os.makedirs(file_dir, exist_ok=True)
        
        # Save with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(file_dir, f"{timestamp}_{os.path.basename(safe_path) or 'index'}.html")
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Content saved to: {filename}")
        return filename
        
    except Exception as e:
        print(f"Error saving content for {url}: {str(e)}")
        return None

def scrape_page(driver, url, depth=0, max_depth=20):
    """Scrape a single page and its subpages up to max_depth"""
    if depth > max_depth or url in visited_urls:
        return
    
    # Calculate progress indicators
    indent = "  " * depth
    progress = f"[Depth {depth}/{max_depth}]"
    print(f"\n{indent}{progress} Scraping: {url}")
    
    try:
        # Navigate to the page
        driver.get(url)
        
        # Check if we landed on the expected page
        current_url = driver.current_url
        if current_url != url and not handle_unexpected_page(driver, url, current_url):
            return
        
        # Add to visited URLs after successful navigation
        visited_urls.add(url)
        
        # Wait for page to fully load
        wait_for_page_load(driver)
        
        # Get the page source after full load
        content = driver.page_source
        soup = BeautifulSoup(content, 'html.parser')
        
        # Save the content
        saved_file = save_page_content(current_url, content)
        print(f"{indent}Saved to: {saved_file}")
        
        # Extract and follow links
        links = extract_links(soup, BASE_URL)
        print(f"{indent}Found {len(links)} relevant links")
        
        # Recursively scrape each link
        for i, link in enumerate(links, 1):
            print(f"{indent}Processing link {i}/{len(links)} at depth {depth}")
            scrape_page(driver, link, depth + 1, max_depth)
            
    except Exception as e:
        print(f"{indent}Error scraping {url}: {str(e)}")
        # Take a screenshot on error for debugging
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = os.path.join(output_dir, f"error_{timestamp}.png")
            driver.save_screenshot(screenshot_path)
            print(f"{indent}Error screenshot saved to: {screenshot_path}")
            
            # Offer manual intervention on error
            if handle_unexpected_page(driver, url, driver.current_url):
                # Try scraping again after manual intervention
                scrape_page(driver, url, depth, max_depth)
        except:
            pass

def main():
    print("Starting WorldQuant Brain scraper...")
    
    # Initialize the driver
    driver = setup_driver()
    
    try:
        # Login
        if not login(driver):
            print("Failed to login. Exiting...")
            return
        
        # Start scraping from each main section
        for start_url in START_URLS:
            print(f"\nStarting to scrape section: {start_url}")
            scrape_page(driver, start_url, depth=0, max_depth=20)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        
    finally:
        print("\nScraping completed!")
        print(f"Total pages scraped: {len(visited_urls)}")
        print("\nScraped URLs:")
        for url in sorted(visited_urls):
            print(f"- {url}")
        input("Press Enter to close the browser...")
        driver.quit()

if __name__ == "__main__":
    main()
