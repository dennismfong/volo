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
        # Get URL from env, default to volosports.com if not set or empty
        volo_url_env = os.getenv('VOLO_URL', '').strip()
        self.volo_url = volo_url_env if volo_url_env else 'https://www.volosports.com'
        
        # Search only mode - finds pickups but doesn't sign up
        search_only_env = os.getenv('SEARCH_ONLY', '').strip().lower()
        self.search_only = search_only_env in ('true', '1', 'yes', 'on')
        
        if not self.email or not self.password:
            raise ValueError("VOLO_EMAIL and VOLO_PASSWORD must be set")
        
        if not self.volo_url:
            raise ValueError("VOLO_URL must be set or default will be used")
        
        if self.search_only:
            logger.info("🔍 SEARCH ONLY MODE: Will find pickups but NOT sign up")
    
    def login(self, page):
        """Login to Volo Sports"""
        try:
            # Navigate directly to login page
            login_url = 'https://www.volosports.com/login'
            logger.info(f"Navigating to login page: {login_url}")
            page.goto(login_url, wait_until='networkidle')
            page.wait_for_timeout(2000)
            
            # Wait for login form to load
            logger.info("Waiting for login form...")
            
            # Enter email - try multiple selectors
            email_selectors = [
                "input[type='email']",
                "input[name='email']",
                "input[placeholder*='email']",
                "input[placeholder*='Email']",
                "input[id*='email']",
                "label:has-text('Email') + input",
                "input[aria-label*='email' i]",
            ]
            
            email_field = None
            for selector in email_selectors:
                try:
                    email_field = page.wait_for_selector(selector, timeout=3000)
                    if email_field:
                        logger.info(f"Found email field using: {selector}")
                        break
                except:
                    continue
            
            if not email_field:
                logger.error("Could not find email field")
                page.screenshot(path='login_email_field_error.png')
                return False
            
            email_field.fill(self.email)
            logger.info("✓ Entered email")
            page.wait_for_timeout(500)
            
            # Enter password - try multiple selectors
            password_selectors = [
                "input[type='password']",
                "input[name='password']",
                "input[placeholder*='password']",
                "input[placeholder*='Password']",
                "input[id*='password']",
                "label:has-text('Password') + input",
                "input[aria-label*='password' i]",
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = page.wait_for_selector(selector, timeout=3000)
                    if password_field:
                        logger.info(f"Found password field using: {selector}")
                        break
                except:
                    continue
            
            if not password_field:
                logger.error("Could not find password field")
                page.screenshot(path='login_password_field_error.png')
                return False
            
            password_field.fill(self.password)
            logger.info("✓ Entered password")
            page.wait_for_timeout(500)
            
            # Click login button - try multiple selectors
            login_button_selectors = [
                "button:has-text('Log in with email')",
                "button:has-text('Log in')",
                "button:has-text('Login')",
                "button[type='submit']",
                "button[class*='login']",
                "button[id*='login']",
                "[data-testid*='login']",
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = page.wait_for_selector(selector, timeout=3000)
                    if login_button and login_button.is_visible():
                        logger.info(f"Found login button using: {selector}")
                        break
                except:
                    continue
            
            if not login_button:
                logger.error("Could not find login button")
                page.screenshot(path='login_button_error.png')
                return False
            
            login_button.click()
            logger.info("✓ Clicked login button")
            
            # Wait for navigation after login
            logger.info("Waiting for login to complete...")
            page.wait_for_timeout(3000)
            
            # Wait for URL to change away from login page
            try:
                # Wait up to 10 seconds for URL to change
                page.wait_for_function(
                    "window.location.href.indexOf('login') === -1",
                    timeout=10000
                )
                current_url = page.url
                logger.info(f"✅ Login successful - redirected to: {current_url}")
                return True
            except:
                # Check current URL
                current_url = page.url
                logger.info(f"Current URL after login attempt: {current_url}")
                
                if "login" not in current_url.lower():
                    logger.info("✅ Login successful - not on login page")
                    return True
                else:
                    logger.warning("Still on login page, checking for errors...")
                    # Check for error messages
                    try:
                        error_elements = page.query_selector_all("text=/error|invalid|incorrect|wrong/i")
                        if error_elements:
                            for elem in error_elements[:3]:  # Check first 3 error elements
                                try:
                                    error_text = elem.inner_text()
                                    if error_text:
                                        logger.error(f"Login error detected: {error_text}")
                                except:
                                    pass
                    except:
                        pass
                    page.screenshot(path='login_failed.png')
                    logger.error("❌ Login failed - still on login page")
                    return False
                
        except Exception as e:
            logger.error(f"Login failed: {e}")
            page.screenshot(path='login_exception.png')
            return False
    
    def find_matching_pickups(self, page):
        """Find all pickup events and filter for 'Volleyball Pickup' with $0 total"""
        try:
            logger.info("Searching for pickup events...")
            page.wait_for_timeout(3000)  # Wait for page to load
            
            # Find all pickup/event cards/items
            # Try multiple selectors that might match the Volo Sports page structure
            pickup_selectors = [
                "div[class*='event']",
                "div[class*='pickup']",
                "div[class*='card']",
                "article",
                "li[class*='event']",
                "[data-testid*='event']",
                "[data-testid*='pickup']",
                "a[href*='/event']",
                "a[href*='/pickup']",
            ]
            
            matching_pickups = []
            events = []
            
            for selector in pickup_selectors:
                try:
                    events = page.query_selector_all(selector)
                    if events and len(events) > 0:
                        logger.info(f"Found {len(events)} potential events using selector: {selector}")
                        break
                except:
                    continue
            
            # If no events found with selectors, try to find by text content
            if not events:
                logger.info("Trying to find events by searching for 'Volleyball Pickup' text...")
                try:
                    # Look for elements containing "Volleyball Pickup"
                    events = page.query_selector_all("text=/Volleyball Pickup/i")
                    if events:
                        # Get parent elements
                        events = [e.evaluate_handle("el => el.closest('div, article, li, a')") for e in events if e]
                        logger.info(f"Found {len(events)} events by text search")
                except:
                    pass
            
            if not events:
                logger.warning("No events found with any selector")
                # Take a screenshot for debugging
                page.screenshot(path='no_events_found.png')
                return []
            
            # Filter events
            for event in events:
                try:
                    # Get the event text/title
                    event_text = (event.inner_text() or '').lower()
                    event_html = (event.inner_html() or '').lower()
                    
                    # Check if title contains "Volleyball Pickup" (exact phrase, case insensitive)
                    if "volleyball pickup" not in event_text and "volleyball pickup" not in event_html:
                        continue
                    
                    # Extract title for logging (first 150 chars)
                    title_match = None
                    try:
                        # Try to find the title element
                        title_elem = event.query_selector("h1, h2, h3, h4, [class*='title'], [class*='name']")
                        if title_elem:
                            title_match = title_elem.inner_text()[:150]
                        else:
                            title_match = event_text[:150]
                    except:
                        title_match = event_text[:150]
                    
                    logger.info(f"Found event with 'Volleyball Pickup' in title: {title_match}")
                    
                    # Check for $0 total
                    # Look for price indicators - check if price is missing, $0, free, or shows no price
                    price_indicators = ["$0", "$0.00", "free", "0.00", "total: $0", "total: $0.00"]
                    price_text_lower = event_text.lower()
                    price_html_lower = event_html.lower()
                    
                    # Check if price is explicitly $0
                    has_free_price = any(indicator in price_text_lower or indicator in price_html_lower for indicator in price_indicators)
                    
                    # Also check if price elements exist and what they say
                    if not has_free_price:
                        try:
                            # Look for price elements
                            price_selectors = [
                                "[class*='price']",
                                "[class*='cost']",
                                "[class*='total']",
                                "[class*='amount']",
                                "[data-testid*='price']",
                            ]
                            for price_selector in price_selectors:
                                try:
                                    price_elements = event.query_selector_all(price_selector)
                                    for price_elem in price_elements:
                                        price_text = (price_elem.inner_text() or '').lower()
                                        # If we find a price element, check its value
                                        if any(indicator in price_text for indicator in price_indicators):
                                            has_free_price = True
                                            break
                                        # If price element exists but is empty or shows no price, might be free
                                        if not price_text.strip() or price_text in ['', 'n/a', 'tbd']:
                                            # Check if there's no "$" symbol at all in the event
                                            if '$' not in event_text and '$' not in event_html:
                                                has_free_price = True
                                                break
                                except:
                                    continue
                                if has_free_price:
                                    break
                        except:
                            pass
                    
                    # If no price indicators found, check if there's NO price mentioned at all
                    # (Some free events might not show a price)
                    if not has_free_price:
                        # Check if there are any dollar signs in the event text/html
                        has_dollar_sign = '$' in event_text or '$' in event_html
                        # If no dollar sign and no explicit price, might be free
                        if not has_dollar_sign:
                            logger.info("  → No price found in event, assuming it might be free")
                            has_free_price = True
                    
                    if has_free_price:
                        logger.info("✓ Event matches criteria: 'Volleyball Pickup' and $0/free")
                        matching_pickups.append(event)
                    else:
                        # Extract price info for logging
                        price_info = "unknown"
                        try:
                            price_elem = event.query_selector("[class*='price'], [class*='cost']")
                            if price_elem:
                                price_info = price_elem.inner_text()
                        except:
                            pass
                        logger.info(f"✗ Event has 'Volleyball Pickup' but price is not $0: {price_info}")
                        
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
            logger.info("Navigating to volleyball pickups page...")
            
            # Navigate directly to the volleyball pickups page
            volleyball_url = os.getenv('VOLO_VOLLEYBALL_URL')
            if not volleyball_url:
                # Default URL for San Francisco volleyball pickups
                volleyball_url = 'https://www.volosports.com/discover?cityName=San%20Francisco&subView=DAILY&view=SPORTS&sportNames%5B0%5D=Volleyball'
            
            logger.info(f"Navigating to: {volleyball_url}")
            
            try:
                # Try navigating with a longer timeout and different wait strategy
                page.goto(volleyball_url, wait_until='domcontentloaded', timeout=60000)
                logger.info("Page navigation started, waiting for content...")
                page.wait_for_timeout(5000)  # Wait for JavaScript to load content
                
                # Check current URL after navigation
                current_url = page.url
                logger.info(f"Current URL after navigation: {current_url}")
                
                # Check if we got redirected to login page
                if 'login' in current_url.lower():
                    logger.warning("Got redirected to login page - login may have failed")
                    page.screenshot(path='redirected_to_login.png')
                    return False
                
                # Take a screenshot to see what loaded
                page.screenshot(path='pickups_page_loaded.png')
                logger.info("✓ Pickups page loaded")
                
            except Exception as e:
                logger.error(f"Error navigating to pickups page: {e}")
                current_url = page.url
                logger.info(f"Current URL when error occurred: {current_url}")
                page.screenshot(path='pickups_page_error.png')
                return False
            
            # Find matching pickups
            matching_pickups = self.find_matching_pickups(page)
            
            if not matching_pickups:
                logger.warning("No matching pickups found (must have 'Volleyball Pickup' in title and $0 total)")
                return False
            
            # Log what we found
            logger.info("=" * 60)
            logger.info(f"Found {len(matching_pickups)} matching pickup(s) for signup:")
            for i, pickup in enumerate(matching_pickups, 1):
                try:
                    pickup_text = pickup.inner_text()[:200] if pickup.inner_text() else "N/A"
                    logger.info(f"  {i}. {pickup_text}")
                except:
                    logger.info(f"  {i}. [Could not extract text]")
            logger.info("=" * 60)
            
            # If search only mode, just log and return
            if self.search_only:
                logger.info("🔍 SEARCH ONLY MODE: Skipping actual signup")
                logger.info(f"Would sign up for {len(matching_pickups)} pickup(s) if not in search-only mode")
                return True
            
            # Sign up for each matching pickup
            signed_up_count = 0
            for pickup in matching_pickups:
                try:
                    logger.info(f"Attempting to sign up for pickup...")
                    
                    # Click on the pickup card/event to go to detail page
                    try:
                        logger.info("Clicking on event to view details...")
                        pickup.click()
                        page.wait_for_timeout(3000)  # Wait for detail page to load
                    except Exception as e:
                        logger.warning(f"Could not click pickup: {e}")
                        continue
                    
                    # On the detail page, we need to:
                    # 1. Check both waiver/agreement checkboxes
                    # 2. Wait for Register button to become enabled
                    # 3. Click Register button
                    
                    try:
                        # Find and check the checkboxes
                        logger.info("Looking for waiver/agreement checkboxes...")
                        
                        # Try multiple selectors for checkboxes
                        checkbox_selectors = [
                            "input[type='checkbox']",
                            "input[type='checkbox']:not(:checked)",
                            "[class*='checkbox'] input",
                            "[class*='waiver'] input[type='checkbox']",
                            "[class*='agreement'] input[type='checkbox']",
                        ]
                        
                        checkboxes = []
                        for selector in checkbox_selectors:
                            try:
                                checkboxes = page.query_selector_all(selector)
                                if checkboxes:
                                    logger.info(f"Found {len(checkboxes)} checkbox(es) using selector: {selector}")
                                    break
                            except:
                                continue
                        
                        # Filter to only unchecked checkboxes
                        unchecked_checkboxes = []
                        for checkbox in checkboxes:
                            try:
                                if not checkbox.is_checked():
                                    unchecked_checkboxes.append(checkbox)
                            except:
                                pass
                        
                        if len(unchecked_checkboxes) >= 2:
                            logger.info(f"Found {len(unchecked_checkboxes)} unchecked checkbox(es), checking them...")
                            for i, checkbox in enumerate(unchecked_checkboxes[:2], 1):  # Check first 2
                                try:
                                    checkbox.check()
                                    logger.info(f"✓ Checked checkbox {i}")
                                    page.wait_for_timeout(500)  # Small delay between checks
                                except Exception as e:
                                    logger.warning(f"Could not check checkbox {i}: {e}")
                        elif len(unchecked_checkboxes) == 1:
                            logger.info("Found 1 unchecked checkbox, checking it...")
                            try:
                                unchecked_checkboxes[0].check()
                                logger.info("✓ Checked checkbox")
                                page.wait_for_timeout(500)
                            except Exception as e:
                                logger.warning(f"Could not check checkbox: {e}")
                        else:
                            logger.warning(f"Expected 2 checkboxes but found {len(unchecked_checkboxes)} unchecked ones")
                        
                        # Wait a moment for Register button to become enabled
                        page.wait_for_timeout(1000)
                        
                        # Now find and click the Register button
                        logger.info("Looking for Register button...")
                        register_button = None
                        register_selectors = [
                            "button:has-text('Register')",
                            "button[class*='register']:not([disabled])",
                            "button[id*='register']:not([disabled])",
                            "[data-testid*='register']:not([disabled])",
                            "button:has-text('Sign Up')",
                            "button:has-text('Join')",
                        ]
                        
                        for selector in register_selectors:
                            try:
                                register_button = page.wait_for_selector(selector, timeout=5000)
                                if register_button:
                                    # Check if button is enabled (not disabled)
                                    is_disabled = register_button.get_attribute('disabled')
                                    if not is_disabled or is_disabled == 'false':
                                        logger.info(f"Found enabled Register button using: {selector}")
                                        break
                                    else:
                                        logger.info("Register button found but is disabled, waiting...")
                                        # Wait a bit more and try again
                                        page.wait_for_timeout(2000)
                                        is_disabled = register_button.get_attribute('disabled')
                                        if not is_disabled or is_disabled == 'false':
                                            break
                                        register_button = None
                            except:
                                continue
                        
                        if register_button:
                            register_button.click()
                            logger.info("✓ Clicked Register button")
                            page.wait_for_timeout(2000)
                            
                            # Check for any confirmation dialogs or success messages
                            try:
                                confirm_selectors = [
                                    "button:has-text('Confirm')",
                                    "button:has-text('Complete')",
                                    "button[class*='confirm']",
                                ]
                                for selector in confirm_selectors:
                                    try:
                                        confirm_button = page.wait_for_selector(selector, timeout=3000)
                                        if confirm_button:
                                            confirm_button.click()
                                            logger.info("✓ Confirmed registration")
                                            break
                                    except:
                                        continue
                            except Exception as e:
                                logger.info(f"No additional confirmation needed: {e}")
                            
                            signed_up_count += 1
                            logger.info(f"✅ Successfully signed up for pickup #{signed_up_count}!")
                            
                        else:
                            logger.warning("Could not find enabled Register button")
                            page.screenshot(path=f'register_button_not_found_{signed_up_count}.png')
                    
                    except Exception as e:
                        logger.error(f"Error during registration process: {e}")
                        page.screenshot(path=f'registration_error_{signed_up_count}.png')
                        continue
                    
                    # Go back to list if needed for next pickup
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
                    logger.info("=" * 60)
                    logger.info("STEP 1: LOGGING IN")
                    logger.info("=" * 60)
                    login_success = self.login(page)
                    
                    if not login_success:
                        logger.error("❌ Login failed - stopping execution")
                        logger.error("Please check your VOLO_EMAIL and VOLO_PASSWORD secrets")
                        page.screenshot(path='login_failed_final.png')
                        return
                    
                    logger.info("=" * 60)
                    logger.info("✅ LOGIN SUCCESSFUL!")
                    logger.info("=" * 60)
                    logger.info("STEP 2: FINDING PICKUPS")
                    logger.info("=" * 60)
                    
                    signup_success = self.signup_for_volleyball(page)
                    
                    if signup_success:
                        logger.info("=" * 60)
                        logger.info("✅ BOT EXECUTION COMPLETED SUCCESSFULLY!")
                        logger.info("=" * 60)
                    else:
                        logger.error("=" * 60)
                        logger.error("❌ SIGNUP/SEARCH FAILED")
                        logger.error("=" * 60)
                finally:
                    browser.close()
                    logger.info("Browser closed")
            
        except Exception as e:
            logger.error(f"Bot execution failed: {e}")


if __name__ == "__main__":
    bot = VoloBot()
    bot.run()
