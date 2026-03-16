#!/usr/bin/env python3
"""
Volo Sports Volleyball Pickup Auto-Signup Bot
Automatically signs up for volleyball pickups at 12:01am daily
"""

import os
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('volo_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class VoloBot:
    def __init__(self):
        self.email = os.getenv('VOLO_EMAIL')
        self.password = os.getenv('VOLO_PASSWORD')
        self.volo_url = os.getenv('VOLO_URL', 'https://www.volosports.com')
        self.driver = None
        
        if not self.email or not self.password:
            raise ValueError("VOLO_EMAIL and VOLO_PASSWORD must be set in .env file")
    
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in background
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        # Uncomment if you want to see the browser (for debugging)
        # chrome_options.headless = False
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            logger.info("Chrome driver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def login(self):
        """Login to Volo Sports"""
        try:
            logger.info(f"Navigating to {self.volo_url}")
            self.driver.get(self.volo_url)
            time.sleep(2)
            
            # Wait for and click login button/link
            # Adjust selectors based on actual Volo Sports website structure
            try:
                login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Login"))
                )
                login_button.click()
                logger.info("Clicked login button")
            except TimeoutException:
                # Try alternative selectors
                try:
                    login_button = self.driver.find_element(By.CSS_SELECTOR, "a[href*='login'], button[class*='login']")
                    login_button.click()
                    logger.info("Clicked login button (alternative selector)")
                except NoSuchElementException:
                    logger.warning("Could not find login button, assuming already on login page")
            
            time.sleep(2)
            
            # Enter email
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.NAME, "email"))
            )
            email_field.clear()
            email_field.send_keys(self.email)
            logger.info("Entered email")
            
            # Enter password
            password_field = self.driver.find_element(By.NAME, "password")
            password_field.clear()
            password_field.send_keys(self.password)
            logger.info("Entered password")
            
            # Submit login form
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
            submit_button.click()
            logger.info("Submitted login form")
            
            time.sleep(3)
            
            # Verify login success
            if "login" not in self.driver.current_url.lower():
                logger.info("Login successful")
                return True
            else:
                logger.error("Login may have failed - still on login page")
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def find_matching_pickups(self):
        """Find all pickup events and filter for 'Volleyball Pickup' with $0 total"""
        try:
            logger.info("Searching for pickup events...")
            time.sleep(2)  # Wait for page to load
            
            # Find all pickup/event cards/items
            # These selectors will need to be adjusted based on actual website structure
            pickup_selectors = [
                "//div[contains(@class, 'event')]",
                "//div[contains(@class, 'pickup')]",
                "//div[contains(@class, 'card')]",
                "//article",
                "//li[contains(@class, 'event')]",
            ]
            
            matching_pickups = []
            events = []
            
            for selector in pickup_selectors:
                try:
                    events = self.driver.find_elements(By.XPATH, selector)
                    if events:
                        logger.info(f"Found {len(events)} potential events using selector: {selector}")
                        break
                except:
                    continue
            
            if not events:
                logger.warning("No events found with any selector")
                return []
            
            # Filter events
            for event in events:
                try:
                    # Get the event text/title
                    event_text = event.text.lower()
                    event_html = event.get_attribute('innerHTML') or ''
                    
                    # Check if title contains "Volleyball Pickup"
                    if "volleyball pickup" not in event_text and "volleyball pickup" not in event_html.lower():
                        continue
                    
                    logger.info(f"Found event with 'Volleyball Pickup' in title: {event_text[:100]}")
                    
                    # Check for $0 total
                    # Look for price indicators: $0, Free, 0.00, etc.
                    price_indicators = ["$0", "$0.00", "free", "0.00", "total: $0", "total: $0.00"]
                    has_free_price = any(indicator in event_text or indicator in event_html.lower() for indicator in price_indicators)
                    
                    if not has_free_price:
                        # Try to find price elements more specifically
                        try:
                            price_elements = event.find_elements(By.XPATH, ".//*[contains(@class, 'price') or contains(@class, 'cost') or contains(@class, 'total')]")
                            for price_elem in price_elements:
                                price_text = price_elem.text.lower()
                                if any(indicator in price_text for indicator in price_indicators):
                                    has_free_price = True
                                    break
                        except:
                            pass
                    
                    if has_free_price:
                        logger.info("✓ Event matches criteria: 'Volleyball Pickup' and $0 total")
                        matching_pickups.append(event)
                    else:
                        logger.info(f"✗ Event has 'Volleyball Pickup' but not $0: {event_text[:100]}")
                        
                except Exception as e:
                    logger.warning(f"Error processing event: {e}")
                    continue
            
            logger.info(f"Found {len(matching_pickups)} matching pickup(s)")
            return matching_pickups
            
        except Exception as e:
            logger.error(f"Error finding pickups: {e}")
            return []
    
    def signup_for_volleyball(self):
        """Navigate to volleyball pickups and sign up for matching events"""
        try:
            # Navigate to volleyball section
            logger.info("Navigating to volleyball pickups")
            
            # Try to find volleyball/pickup link
            try:
                volleyball_link = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Volleyball"))
                )
                volleyball_link.click()
                time.sleep(2)
            except TimeoutException:
                # Try alternative navigation
                try:
                    volleyball_link = self.driver.find_element(By.CSS_SELECTOR, "a[href*='volleyball'], a[href*='pickup']")
                    volleyball_link.click()
                    time.sleep(2)
                except NoSuchElementException:
                    logger.warning("Could not find volleyball link, trying direct URL")
                    volleyball_url = os.getenv('VOLO_VOLLEYBALL_URL')
                    if volleyball_url:
                        self.driver.get(volleyball_url)
                        time.sleep(2)
            
            # Find matching pickups
            matching_pickups = self.find_matching_pickups()
            
            if not matching_pickups:
                logger.warning("No matching pickups found (must have 'Volleyball Pickup' in title and $0 total)")
                return False
            
            # Sign up for each matching pickup
            signed_up_count = 0
            for pickup in matching_pickups:
                try:
                    logger.info(f"Attempting to sign up for pickup...")
                    
                    # Try to find signup button within this pickup element
                    signup_button = None
                    selectors = [
                        (By.XPATH, ".//button[contains(text(), 'Sign Up')]"),
                        (By.XPATH, ".//a[contains(text(), 'Sign Up')]"),
                        (By.XPATH, ".//button[contains(@class, 'signup')]"),
                        (By.XPATH, ".//a[contains(@class, 'signup')]"),
                        (By.XPATH, ".//button[contains(@id, 'signup')]"),
                        (By.XPATH, ".//a[contains(@id, 'signup')]"),
                    ]
                    
                    for selector_type, selector_value in selectors:
                        try:
                            signup_button = pickup.find_element(selector_type, selector_value)
                            if signup_button and signup_button.is_displayed():
                                break
                        except:
                            continue
                    
                    # If not found within pickup, try clicking the pickup itself
                    if not signup_button:
                        try:
                            pickup.click()
                            time.sleep(2)
                            # Now try to find signup button on the detail page
                            signup_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Sign Up')] | //a[contains(text(), 'Sign Up')]"))
                            )
                        except:
                            logger.warning("Could not find signup button for this pickup")
                            continue
                    
                    if signup_button:
                        signup_button.click()
                        logger.info("Clicked signup button")
                        time.sleep(2)
                        
                        # Confirm signup if needed
                        try:
                            confirm_selectors = [
                                (By.XPATH, "//button[contains(text(), 'Confirm')]"),
                                (By.CSS_SELECTOR, "button[class*='confirm']"),
                            ]
                            for selector_type, selector_value in confirm_selectors:
                                try:
                                    confirm_button = WebDriverWait(self.driver, 3).until(
                                        EC.element_to_be_clickable((selector_type, selector_value))
                                    )
                                    confirm_button.click()
                                    logger.info("Confirmed signup")
                                    break
                                except TimeoutException:
                                    continue
                        except Exception as e:
                            logger.info(f"No confirmation needed: {e}")
                        
                        signed_up_count += 1
                        logger.info(f"Successfully signed up for pickup #{signed_up_count}!")
                        
                        # Go back if needed for next pickup
                        time.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error signing up for pickup: {e}")
                    continue
            
            if signed_up_count > 0:
                logger.info(f"Successfully signed up for {signed_up_count} matching pickup(s)!")
                return True
            else:
                logger.warning("Found matching pickups but could not sign up for any")
                self.driver.save_screenshot('signup_error.png')
                return False
                
        except Exception as e:
            logger.error(f"Signup failed: {e}")
            self.driver.save_screenshot('signup_error.png')
            return False
    
    def run(self):
        """Main execution method"""
        try:
            logger.info("=" * 50)
            logger.info(f"Starting Volo Bot at {datetime.now()}")
            logger.info("=" * 50)
            
            self.setup_driver()
            
            if self.login():
                if self.signup_for_volleyball():
                    logger.info("Bot execution completed successfully!")
                else:
                    logger.error("Signup failed")
            else:
                logger.error("Login failed")
            
        except Exception as e:
            logger.error(f"Bot execution failed: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("Browser closed")


if __name__ == "__main__":
    bot = VoloBot()
    bot.run()
