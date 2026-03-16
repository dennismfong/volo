#!/usr/bin/env python3
"""
Volo Sports Volleyball Pickup Auto-Signup Bot (GitHub Actions Optimized)
Uses Playwright instead of Selenium for better CI/CD compatibility
"""

import os
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
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
        
        if not self.email or not self.password:
            raise ValueError("VOLO_EMAIL and VOLO_PASSWORD must be set")
    
    def login(self, page):
        """Login to Volo Sports"""
        try:
            logger.info(f"Navigating to {self.volo_url}")
            page.goto(self.volo_url, wait_until='networkidle')
            
            # Wait for and click login button/link
            try:
                page.click("text=Login", timeout=10000)
                logger.info("Clicked login button")
            except PlaywrightTimeoutError:
                # Try alternative selectors
                try:
                    page.click("a[href*='login'], button:has-text('Login')", timeout=5000)
                    logger.info("Clicked login button (alternative selector)")
                except PlaywrightTimeoutError:
                    logger.warning("Could not find login button, assuming already on login page")
            
            page.wait_for_timeout(2000)
            
            # Enter email
            email_field = page.wait_for_selector("input[name='email'], input[type='email']", timeout=10000)
            email_field.fill(self.email)
            logger.info("Entered email")
            
            # Enter password
            password_field = page.wait_for_selector("input[name='password'], input[type='password']", timeout=10000)
            password_field.fill(self.password)
            logger.info("Entered password")
            
            # Submit login form
            page.click("button[type='submit'], input[type='submit']")
            logger.info("Submitted login form")
            
            page.wait_for_timeout(3000)
            
            # Verify login success
            if "login" not in page.url.lower():
                logger.info("Login successful")
                return True
            else:
                logger.error("Login may have failed - still on login page")
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def find_matching_pickups(self, page):
        """Find all pickup events and filter for 'Volleyball Pickup' with $0 total"""
        try:
            logger.info("Searching for pickup events...")
            page.wait_for_timeout(2000)  # Wait for page to load
            
            # Find all pickup/event cards/items
            pickup_selectors = [
                "div[class*='event']",
                "div[class*='pickup']",
                "div[class*='card']",
                "article",
                "li[class*='event']",
            ]
            
            matching_pickups = []
            events = []
            
            for selector in pickup_selectors:
                try:
                    events = page.query_selector_all(selector)
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
                    event_text = (event.inner_text() or '').lower()
                    event_html = (event.inner_html() or '').lower()
                    
                    # Check if title contains "Volleyball Pickup"
                    if "volleyball pickup" not in event_text and "volleyball pickup" not in event_html:
                        continue
                    
                    logger.info(f"Found event with 'Volleyball Pickup' in title: {event_text[:100]}")
                    
                    # Check for $0 total
                    price_indicators = ["$0", "$0.00", "free", "0.00", "total: $0", "total: $0.00"]
                    has_free_price = any(indicator in event_text or indicator in event_html for indicator in price_indicators)
                    
                    if not has_free_price:
                        # Try to find price elements more specifically
                        try:
                            price_elements = event.query_selector_all("[class*='price'], [class*='cost'], [class*='total']")
                            for price_elem in price_elements:
                                price_text = (price_elem.inner_text() or '').lower()
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
    
    def signup_for_volleyball(self, page):
        """Navigate to volleyball pickups and sign up for matching events"""
        try:
            logger.info("Navigating to volleyball pickups")
            
            # Try to find volleyball/pickup link
            try:
                page.click("text=Volleyball", timeout=10000)
                page.wait_for_timeout(2000)
            except PlaywrightTimeoutError:
                try:
                    page.click("a[href*='volleyball'], a[href*='pickup']", timeout=5000)
                    page.wait_for_timeout(2000)
                except PlaywrightTimeoutError:
                    volleyball_url = os.getenv('VOLO_VOLLEYBALL_URL')
                    if volleyball_url:
                        logger.info(f"Navigating directly to {volleyball_url}")
                        page.goto(volleyball_url, wait_until='networkidle')
                        page.wait_for_timeout(2000)
                    else:
                        logger.warning("Could not find volleyball link")
            
            # Find matching pickups
            matching_pickups = self.find_matching_pickups(page)
            
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
                    signup_selectors = [
                        "button:has-text('Sign Up')",
                        "a:has-text('Sign Up')",
                        "button[class*='signup']",
                        "a[class*='signup']",
                        "button[id*='signup']",
                        "a[id*='signup']",
                    ]
                    
                    for selector in signup_selectors:
                        try:
                            signup_button = pickup.query_selector(selector)
                            if signup_button:
                                break
                        except:
                            continue
                    
                    # If not found within pickup, try clicking the pickup itself
                    if not signup_button:
                        try:
                            pickup.click()
                            page.wait_for_timeout(2000)
                            # Now try to find signup button on the detail page
                            for selector in signup_selectors:
                                try:
                                    signup_button = page.wait_for_selector(selector, timeout=3000)
                                    if signup_button:
                                        break
                                except:
                                    continue
                        except:
                            logger.warning("Could not find signup button for this pickup")
                            continue
                    
                    if signup_button:
                        signup_button.click()
                        logger.info("Clicked signup button")
                        page.wait_for_timeout(2000)
                        
                        # Confirm signup if needed
                        try:
                            confirm_selectors = [
                                "button:has-text('Confirm')",
                                "button[class*='confirm']",
                            ]
                            for selector in confirm_selectors:
                                try:
                                    confirm_button = page.wait_for_selector(selector, timeout=3000)
                                    if confirm_button:
                                        confirm_button.click()
                                        logger.info("Confirmed signup")
                                        break
                                except:
                                    continue
                        except Exception as e:
                            logger.info(f"No confirmation needed: {e}")
                        
                        signed_up_count += 1
                        logger.info(f"Successfully signed up for pickup #{signed_up_count}!")
                        
                        # Go back if needed for next pickup
                        page.wait_for_timeout(1000)
                        
                except Exception as e:
                    logger.error(f"Error signing up for pickup: {e}")
                    continue
            
            if signed_up_count > 0:
                logger.info(f"Successfully signed up for {signed_up_count} matching pickup(s)!")
                return True
            else:
                logger.warning("Found matching pickups but could not sign up for any")
                page.screenshot(path='signup_error.png')
                return False
                
        except Exception as e:
            logger.error(f"Signup failed: {e}")
            page.screenshot(path='signup_error.png')
            return False
    
    def run(self):
        """Main execution method"""
        try:
            logger.info("=" * 50)
            logger.info(f"Starting Volo Bot at {datetime.now()}")
            logger.info("=" * 50)
            
            with sync_playwright() as p:
                # Launch browser
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = context.new_page()
                
                try:
                    if self.login(page):
                        if self.signup_for_volleyball(page):
                            logger.info("Bot execution completed successfully!")
                        else:
                            logger.error("Signup failed")
                    else:
                        logger.error("Login failed")
                finally:
                    browser.close()
                    logger.info("Browser closed")
            
        except Exception as e:
            logger.error(f"Bot execution failed: {e}")


if __name__ == "__main__":
    bot = VoloBot()
    bot.run()
