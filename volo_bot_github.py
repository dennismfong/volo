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
        # Get cookie from env - if provided, can skip login
        self.cookie = os.getenv('VOLO_COOKIE', '').strip()
        
        # Get URL from env, default to volosports.com if not set or empty
        volo_url_env = os.getenv('VOLO_URL', '').strip()
        self.volo_url = volo_url_env if volo_url_env else 'https://www.volosports.com'
        
        # Search only mode - finds pickups but doesn't sign up
        search_only_env = os.getenv('SEARCH_ONLY', '').strip().lower()
        self.search_only = search_only_env in ('true', '1', 'yes', 'on')
        
        # Validate: need either cookie OR email/password
        if not self.cookie:
            if not self.email or not self.password:
                raise ValueError("Either VOLO_COOKIE must be set, or both VOLO_EMAIL and VOLO_PASSWORD must be set")
        else:
            logger.info("🍪 Cookie provided - will skip login step")
        
        if not self.volo_url:
            raise ValueError("VOLO_URL must be set or default will be used")
        
        if self.search_only:
            logger.info("🔍 SEARCH ONLY MODE: Will find pickups but NOT sign up")
    
    def set_cookie_from_string(self, page, cookie_string):
        """Set cookies from a cookie string (format: 'name=value; name2=value2')"""
        try:
            if not cookie_string or not cookie_string.strip():
                logger.warning("VOLO_COOKIE is empty")
                return False
            
            # Parse cookie string
            cookies = []
            cookie_parts = cookie_string.split(';')
            
            logger.debug(f"Parsing cookie string with {len(cookie_parts)} parts")
            
            for part in cookie_parts:
                part = part.strip()
                if not part:  # Skip empty parts
                    continue
                    
                if '=' in part:
                    name, value = part.split('=', 1)
                    name = name.strip()
                    value = value.strip()
                    
                    if name and value:  # Both must be non-empty
                        # Create cookie object for Playwright
                        cookie = {
                            'name': name,
                            'value': value,
                            'domain': '.volosports.com',  # Use wildcard domain
                            'path': '/',
                        }
                        cookies.append(cookie)
                        logger.debug(f"  Parsed cookie: {name}=...")
                else:
                    logger.debug(f"  Skipping invalid cookie part: {part[:50]}")
            
            if cookies:
                # Navigate to the domain first to set cookies
                logger.info(f"Setting {len(cookies)} cookie(s)...")
                page.goto('https://www.volosports.com', wait_until='domcontentloaded', timeout=15000)
                page.context.add_cookies(cookies)
                logger.info(f"✅ Set {len(cookies)} cookie(s) from VOLO_COOKIE")
                return True
            else:
                logger.warning("No valid cookies found in VOLO_COOKIE (no name=value pairs found)")
                logger.debug(f"Cookie string sample: {cookie_string[:100]}")
                return False
        except Exception as e:
            logger.error(f"Error setting cookies: {e}")
            logger.debug(f"Cookie string that failed: {cookie_string[:100] if cookie_string else 'None'}")
            return False
    
    def login(self, page):
        """Login to Volo Sports - uses cookie if available, otherwise uses email/password"""
        # If cookie is provided, use it instead of logging in
        if self.cookie:
            logger.info("=" * 60)
            logger.info("STEP 1: USING COOKIE (SKIPPING LOGIN)")
            logger.info("=" * 60)
            
            if self.set_cookie_from_string(page, self.cookie):
                # Verify cookie works by navigating to a protected page
                try:
                    page.goto('https://www.volosports.com/app/dashboard', wait_until='domcontentloaded', timeout=10000)
                    current_url = page.url
                    
                    # Check if we're logged in (not redirected to login)
                    if "login" not in current_url.lower():
                        logger.info(f"✅ Cookie authentication successful - on: {current_url}")
                        return True
                    else:
                        logger.warning("Cookie may be invalid - redirected to login page")
                        logger.info("Falling back to email/password login...")
                        # Fall through to email/password login
                except Exception as e:
                    logger.warning(f"Error verifying cookie: {e}")
                    logger.info("Falling back to email/password login...")
                    # Fall through to email/password login
            else:
                logger.warning("Failed to set cookie, falling back to email/password login...")
                # Fall through to email/password login
        
        # Email/password login (original method)
        if not self.email or not self.password:
            logger.error("No cookie provided and no email/password available")
            return False
        
        try:
            logger.info("=" * 60)
            logger.info("STEP 1: LOGGING IN")
            logger.info("=" * 60)
            
            # Navigate directly to login page
            login_url = 'https://www.volosports.com/login'
            logger.info(f"Navigating to login page: {login_url}")
            try:
                page.goto(login_url, wait_until='domcontentloaded', timeout=15000)
                page.wait_for_timeout(2000)
            except Exception as e:
                logger.error(f"Failed to navigate to login page: {e}")
                # Try with networkidle as fallback
                try:
                    page.goto(login_url, wait_until='networkidle', timeout=15000)
                    page.wait_for_timeout(2000)
                except Exception as e2:
                    logger.error(f"Failed to navigate to login page (fallback): {e2}")
                    return False
            
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
            
            # Wait for URL to change away from login page
            # Use multiple strategies to detect successful login
            login_successful = False
            max_wait_time = 20000  # 20 seconds total
            start_time = page.evaluate("Date.now()")
            
            try:
                # Strategy 1: Wait for navigation event
                try:
                    with page.expect_navigation(timeout=15000, wait_until="domcontentloaded"):
                        pass  # Navigation should happen after click
                    current_url = page.url
                    if "login" not in current_url.lower():
                        logger.info(f"✅ Login successful - navigated to: {current_url}")
                        login_successful = True
                except:
                    pass
                
                # Strategy 2: Poll for URL change
                if not login_successful:
                    for attempt in range(20):  # Check every 1 second for 20 seconds
                        page.wait_for_timeout(1000)
                        current_url = page.url
                        if "login" not in current_url.lower():
                            logger.info(f"✅ Login successful - URL changed to: {current_url}")
                            login_successful = True
                            break
                        # Check if we're on dashboard/app page
                        if "dashboard" in current_url.lower() or "app" in current_url.lower():
                            logger.info(f"✅ Login successful - on dashboard/app: {current_url}")
                            login_successful = True
                            break
                
                if login_successful:
                    return True
                
                # If still not successful, check current state
                current_url = page.url
                logger.info(f"Current URL after login attempt: {current_url}")
                
                # Final check - maybe we're already logged in
                if "login" not in current_url.lower():
                    logger.info("✅ Login successful - not on login page")
                    return True
                
                # Still on login page, check for errors
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
                logger.error(f"Error during login verification: {e}")
                page.screenshot(path='login_verification_error.png')
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
                    # Use locator to find elements containing "Volleyball Pickup"
                    # Then get their parent containers
                    text_locators = page.locator("text=/Volleyball Pickup/i")
                    count = text_locators.count()
                    
                    if count > 0:
                        events = []
                        for i in range(count):
                            try:
                                text_locator = text_locators.nth(i)
                                # Find the smallest container that contains this event
                                # Use evaluate to find the closest parent that contains the event but not other events
                                event_elem = text_locator.evaluate_handle("""
                                    el => {
                                        // Walk up the DOM tree to find the event container
                                        // Stop when we find a container that:
                                        // 1. Contains "Volleyball Pickup" (this event)
                                        // 2. Has reasonable size (50-300 chars) - not too small, not containing all events
                                        let current = el;
                                        let bestMatch = null;
                                        
                                        for (let level = 0; level < 6; level++) {
                                            if (!current || !current.parentElement) break;
                                            current = current.parentElement;
                                            const text = (current.innerText || '').toLowerCase();
                                            const textLength = text.length;
                                            
                                            // Check if this container has "volleyball pickup"
                                            if (text.includes('volleyball pickup')) {
                                                // Prefer containers that are event-sized (not too large)
                                                // If text is 50-300 chars, it's likely a single event
                                                if (textLength >= 50 && textLength <= 300) {
                                                    return current;
                                                }
                                                // Remember the first container with "volleyball pickup" as fallback
                                                if (!bestMatch) {
                                                    bestMatch = current;
                                                }
                                            }
                                        }
                                        // Return best match or the original element's closest div
                                        return bestMatch || el.closest('div') || el;
                                    }
                                """)
                                
                                if event_elem:
                                    events.append(event_elem)
                            except Exception as e:
                                logger.debug(f"Error getting event container: {e}")
                                pass
                        logger.info(f"Found {len(events)} events by text search")
                except Exception as e:
                    logger.debug(f"Error finding events by text: {e}")
                    # Fallback: try simple text search and walk up DOM tree
                    try:
                        text_elements = page.query_selector_all("text=/Volleyball Pickup/i")
                        if text_elements:
                            events = []
                            for text_elem in text_elements:
                                try:
                                    # Walk up the DOM tree to find a parent with substantial content
                                    # Use evaluate to get parent elements
                                    parent_handles = text_elem.evaluate("""
                                        el => {
                                            const parents = [];
                                            let current = el;
                                            for (let i = 0; i < 8; i++) {
                                                if (!current || !current.parentElement) break;
                                                current = current.parentElement;
                                                const text = current.innerText || '';
                                                if (text.length > 80) {  // Substantial content
                                                    parents.push({ level: i, textLength: text.length });
                                                }
                                            }
                                            return parents;
                                        }
                                    """)
                                    
                                    # Now actually get the parent element
                                    # Walk up and find the best parent
                                    current_elem = text_elem
                                    best_parent = None
                                    best_length = 0
                                    
                                    for level in range(8):
                                        try:
                                            # Get parent using evaluate_handle
                                            parent_js = current_elem.evaluate_handle("el => el.parentElement")
                                            if not parent_js:
                                                break
                                            
                                            # Convert JSHandle to ElementHandle if possible
                                            # Actually, we need to use a different approach
                                            # Let's use evaluate to get a selector for the parent, then query it
                                            parent_info = current_elem.evaluate("""
                                                el => {
                                                    const parent = el.parentElement;
                                                    if (!parent) return null;
                                                    const text = parent.innerText || '';
                                                    return { textLength: text.length, hasPrice: text.includes('$') };
                                                }
                                            """)
                                            
                                            if parent_info and parent_info['textLength'] > best_length:
                                                best_length = parent_info['textLength']
                                                # Get parent by walking up with a different method
                                                # Use xpath to get parent
                                                try:
                                                    parent_xpath = current_elem.evaluate("el => { const xpath = getXPath(el.parentElement); return xpath; }")
                                                except:
                                                    pass
                                            
                                            # Try to get parent using a simpler method
                                            try:
                                                # Use evaluate to get parent's innerHTML length as a way to identify it
                                                parent_text_len = current_elem.evaluate("el => el.parentElement ? (el.parentElement.innerText || '').length : 0")
                                                if parent_text_len > best_length:
                                                    best_length = parent_text_len
                                                    # We'll get the parent differently
                                            except:
                                                pass
                                            
                                            # Move to next level
                                            try:
                                                current_elem = current_elem.evaluate_handle("el => el.parentElement")
                                                if not current_elem:
                                                    break
                                            except:
                                                break
                                        except:
                                            break
                                    
                                    # For now, just use the text element's closest div parent
                                    # We'll rely on inner_text() to get all nested content
                                    try:
                                        # Get a parent div by evaluating
                                        parent_div = text_elem.evaluate("""
                                            el => {
                                                let current = el;
                                                for (let i = 0; i < 5; i++) {
                                                    if (!current) break;
                                                    if (current.tagName === 'DIV' && (current.innerText || '').length > 80) {
                                                        return true;  // Found a good parent
                                                    }
                                                    current = current.parentElement;
                                                }
                                                return false;
                                            }
                                        """)
                                        
                                        # Since we can't easily get the ElementHandle, 
                                        # we'll use the text element itself and rely on getting all text from it
                                        # The key is to make sure we check all nested divs when checking prices
                                        events.append(text_elem)
                                    except:
                                        events.append(text_elem)  # Use the text element as fallback
                                        
                                except Exception as e:
                                    logger.debug(f"Error processing text element: {e}")
                                    pass
                            
                            if events:
                                logger.info(f"Found {len(events)} events by text search (fallback)")
                    except Exception as e:
                        logger.debug(f"Fallback text search error: {e}")
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
                    # Extract concise title for logging (first line only, max 80 chars)
                    try:
                        # Try to find the title element
                        title_elem = event.query_selector("h1, h2, h3, h4, [class*='title'], [class*='name']")
                        if title_elem:
                            title_match = title_elem.inner_text().split('\n')[0].strip()
                        else:
                            # Use first line of event text
                            title_match = event_text.split('\n')[0].strip() if '\n' in event_text else event_text
                        
                        # Limit to 80 chars
                        if len(title_match) > 80:
                            title_match = title_match[:80] + "..."
                    except:
                        title_match = event_text[:80] if len(event_text) > 80 else event_text
                    
                    logger.info(f"Found event: {title_match}")
                    
                    # Check for $0 total
                    # Price is in a separate div (not in the title), listed under the time on the far right
                    # The price text may be split: "$" in one text node, "10" in another
                    # If there's NO price in any div, it's free
                    has_free_price = False
                    has_price_element = False
                    found_price_value = None
                    
                    try:
                        import re
                        
                        # FIRST: Check the entire event element (including all child divs) for price patterns
                        # The price is in a div under text, and "$" and "10" are separate text nodes in the same div
                        # inner_text() should combine them, but we need to check each div individually
                        
                        # Get text from the event element itself
                        # The event element should already be the right container (not containing all events)
                        # Check prices only within this specific event container
                        all_text = event_text  # Start with the event's own text
                        
                        # Also check all divs within THIS event element (not parent containers)
                        # This ensures we only check prices for this specific event
                        try:
                            # Get all divs within the event element
                            event_divs = event.query_selector_all("div")
                            
                            for div in event_divs:
                                try:
                                    div_text = div.inner_text() or ""
                                    if div_text.strip():
                                        # Only add text that's relevant to this event
                                        # Check if this div contains the event title or price indicators
                                        div_text_lower = div_text.lower()
                                        if "volleyball pickup" in div_text_lower or "$" in div_text or any(char.isdigit() for char in div_text):
                                            all_text += " " + div_text.lower()
                                except:
                                    pass
                        except Exception as e:
                            logger.debug(f"  Error checking divs: {e}")
                            pass
                        
                        # Also check all span elements
                        try:
                            all_spans = event.query_selector_all("span")
                            for span in all_spans:
                                try:
                                    span_text = span.inner_text() or ""
                                    if span_text.strip() and "$" in span_text:
                                        all_text += " " + span_text.lower()
                                except:
                                    pass
                        except:
                            pass
                        
                        # Look for $X or $X.XX patterns in all combined text
                        # inner_text() should have combined "$" and "10" into "$10" if they're in the same div
                        price_matches = re.findall(r'\$[\d.]+', all_text)
                        
                        # Log what we found (concise)
                        if price_matches:
                            logger.debug(f"  Found price patterns: {price_matches}")
                        
                        # If no price pattern found, check for split text nodes:
                        # Look for "$" and numbers in the same parent element
                        if not price_matches:
                            try:
                                # Check all divs - look for divs that contain "$" 
                                # and check if the div's text (which combines all child text nodes) has prices
                                all_divs = event.query_selector_all("div")
                                for div in all_divs:
                                    try:
                                        div_text = div.inner_text() or ""  # inner_text() combines all text nodes
                                        # Check if div has "$" 
                                        if "$" in div_text:
                                            # inner_text() should have combined "$" and "10" if they're in the same div
                                            div_prices = re.findall(r'\$[\d.]+', div_text)
                                            if div_prices:
                                                price_matches.extend(div_prices)
                                                break
                                            # If still no match, "$" and number might be in separate divs
                                            # Check if there's a number nearby
                                            if re.search(r'\d', div_text):
                                                # Try to find $ and number close together
                                                dollar_pos = div_text.find("$")
                                                if dollar_pos >= 0:
                                                    # Get text around $ (20 chars before and after)
                                                    start = max(0, dollar_pos - 5)
                                                    end = min(len(div_text), dollar_pos + 15)
                                                    context = div_text[start:end]
                                                    # Look for number after $
                                                    numbers = re.findall(r'\d+\.?\d*', context)
                                                    if numbers:
                                                        price_matches.append(f"${numbers[0]}")
                                                        break
                                    except:
                                        continue
                                
                                # Also check spans (prices might be in spans)
                                if not price_matches:
                                    all_spans = event.query_selector_all("span")
                                    for span in all_spans:
                                        try:
                                            span_text = span.inner_text() or ""
                                            if "$" in span_text:
                                                span_prices = re.findall(r'\$[\d.]+', span_text)
                                                if span_prices:
                                                    price_matches.extend(span_prices)
                                                    break
                                        except:
                                            continue
                            except Exception as e:
                                logger.debug(f"  Error checking split text nodes: {e}")
                                pass
                        
                        if price_matches:
                            # Found price patterns
                            has_price_element = True
                            found_price_value = ', '.join(price_matches)
                            
                            # Filter out $0 prices and check if any non-zero prices exist
                            non_zero_prices = [p for p in price_matches if p not in ['$0', '$0.00', '$0.0', '$0.']]
                            
                            if non_zero_prices:
                                # Has prices that are not $0
                                has_free_price = False
                                logger.info(f"    → NOT free")
                            elif any(p in ['$0', '$0.00', '$0.0'] for p in price_matches):
                                # Only $0 prices found
                                has_free_price = True
                                logger.info("    → FREE")
                            else:
                                # Has price patterns but unclear - be conservative
                                has_free_price = False
                                logger.info(f"    → NOT free")
                        else:
                            # No price patterns found, try looking for price elements in divs
                            # Look for divs that might contain prices
                            try:
                                # Search for divs that contain price-like text
                                all_divs = event.query_selector_all("div")
                                for div in all_divs:
                                    try:
                                        div_text = div.inner_text() or ""
                                        # Check if div contains price patterns
                                        div_prices = re.findall(r'\$[\d.]+', div_text)
                                        if div_prices:
                                            has_price_element = True
                                            found_price_value = ', '.join(div_prices)
                                            
                                            non_zero = [p for p in div_prices if p not in ['$0', '$0.00', '$0.0']]
                                            if non_zero:
                                                has_free_price = False
                                                logger.info(f"    → NOT free")
                                                break
                                            elif any(p in ['$0', '$0.00', '$0.0'] for p in div_prices):
                                                has_free_price = True
                                                logger.info(f"    → FREE")
                                                break
                                    except:
                                        continue
                            except:
                                pass
                            
                            # Also try standard price selectors
                            if not has_price_element:
                                price_selectors = [
                                    "[class*='price']",
                                    "[class*='cost']",
                                    "[class*='amount']",
                                    "[class*='fee']",
                                    "[data-testid*='price']",
                                ]
                                
                                for price_selector in price_selectors:
                                    try:
                                        price_elements = event.query_selector_all(price_selector)
                                        if price_elements:
                                            for price_elem in price_elements:
                                                price_text = (price_elem.inner_text() or '').strip()
                                                if price_text:
                                                    has_price_element = True
                                                    found_price_value = price_text
                                                    
                                                    # Check for price patterns
                                                    elem_price_matches = re.findall(r'\$[\d.]+', price_text)
                                                    if elem_price_matches:
                                                        non_zero = [p for p in elem_price_matches if p not in ['$0', '$0.00', '$0.0']]
                                                        if non_zero:
                                                            has_free_price = False
                                                            logger.info(f"    → NOT free")
                                                            break
                                                        elif any(p in ['$0', '$0.00', '$0.0'] for p in elem_price_matches):
                                                            has_free_price = True
                                                            logger.info(f"    → FREE")
                                                            break
                                            if has_price_element:
                                                break
                                    except:
                                        continue
                            
                            # If still no price found, it's FREE
                            if not has_price_element:
                                has_free_price = True
                                logger.info("    → FREE")
                    
                    except Exception as e:
                        logger.warning(f"  Error checking price: {e}")
                        # If we can't determine, be conservative and assume it's not free
                        has_free_price = False
                        found_price_value = "error checking"
                    
                    if has_free_price:
                        logger.info("    ✓ Matches criteria")
                        # Try to extract the URL/link for this event
                        event_url = None
                        try:
                            # Look for a link element within the event
                            link = event.query_selector("a[href]")
                            if link:
                                href = link.get_attribute("href")
                                if href:
                                    # Make absolute URL if relative
                                    if href.startswith("/"):
                                        event_url = f"https://www.volosports.com{href}"
                                    elif href.startswith("http"):
                                        event_url = href
                                    else:
                                        event_url = f"https://www.volosports.com/{href}"
                            
                            # Strategy 2: Check if the event itself is a link
                            if not event_url:
                                try:
                                    event_tag = event.evaluate("el => el.tagName.toLowerCase()")
                                    if event_tag == 'a':
                                        href = event.get_attribute("href")
                                        if href:
                                            if href.startswith("/"):
                                                event_url = f"https://www.volosports.com{href}"
                                            elif href.startswith("http"):
                                                event_url = href
                                            else:
                                                event_url = f"https://www.volosports.com/{href}"
                                except:
                                    pass
                            
                            # Strategy 3: Check for data attributes or onclick handlers
                            if not event_url:
                                try:
                                    data_url = event.get_attribute("data-url")
                                    data_href = event.get_attribute("data-href")
                                    data_link = event.get_attribute("data-link")
                                    
                                    if data_url:
                                        event_url = data_url if data_url.startswith("http") else f"https://www.volosports.com{data_url}"
                                    elif data_href:
                                        event_url = data_href if data_href.startswith("http") else f"https://www.volosports.com{data_href}"
                                    elif data_link:
                                        event_url = data_link if data_link.startswith("http") else f"https://www.volosports.com{data_link}"
                                    else:
                                        onclick = event.get_attribute("onclick")
                                        if onclick and "location.href" in onclick:
                                            # Extract URL from onclick handler
                                            import re
                                            url_match = re.search(r"location\.href\s*=\s*['\"]([^'\"]+)['\"]", onclick)
                                            if url_match:
                                                url = url_match.group(1)
                                                event_url = url if url.startswith("http") else f"https://www.volosports.com{url}"
                                except:
                                    pass
                            
                            # Strategy 4: Use evaluate to find any clickable parent that has href
                            if not event_url:
                                try:
                                    url_from_eval = event.evaluate("""
                                        el => {
                                            // Walk up the DOM to find a link
                                            let current = el;
                                            for (let i = 0; i < 5; i++) {
                                                if (!current) break;
                                                if (current.tagName === 'A' && current.href) {
                                                    return current.href;
                                                }
                                                if (current.onclick && current.onclick.toString().includes('location.href')) {
                                                    const match = current.onclick.toString().match(/location\\.href\\s*=\\s*['"]([^'"]+)['"]/);
                                                    if (match) return match[1];
                                                }
                                                if (current.dataset && (current.dataset.url || current.dataset.href || current.dataset.link)) {
                                                    return current.dataset.url || current.dataset.href || current.dataset.link;
                                                }
                                                current = current.parentElement;
                                            }
                                            return null;
                                        }
                                    """)
                                    if url_from_eval:
                                        if url_from_eval.startswith("/"):
                                            event_url = f"https://www.volosports.com{url_from_eval}"
                                        elif url_from_eval.startswith("http"):
                                            event_url = url_from_eval
                                        else:
                                            event_url = f"https://www.volosports.com/{url_from_eval}"
                                except:
                                    pass
                            
                            # Strategy 5: Try to get URL by checking if element has a click handler that navigates
                            if not event_url:
                                try:
                                    # Check if clicking would navigate - get the URL from navigation
                                    url_from_click = event.evaluate("""
                                        el => {
                                            // Check for router/navigation attributes (React, Vue, etc.)
                                            if (el.getAttribute && el.getAttribute('data-href')) {
                                                return el.getAttribute('data-href');
                                            }
                                            // Check for React Router link
                                            if (el.__reactInternalInstance || el.__reactFiber) {
                                                let fiber = el.__reactInternalInstance || el.__reactFiber;
                                                while (fiber) {
                                                    if (fiber.memoizedProps && fiber.memoizedProps.to) {
                                                        return fiber.memoizedProps.to;
                                                    }
                                                    if (fiber.memoizedProps && fiber.memoizedProps.href) {
                                                        return fiber.memoizedProps.href;
                                                    }
                                                    fiber = fiber.return;
                                                }
                                            }
                                            // Check for common navigation patterns
                                            let clickable = el;
                                            for (let i = 0; i < 3; i++) {
                                                if (!clickable) break;
                                                // Check for data attributes
                                                const attrs = clickable.attributes;
                                                if (attrs) {
                                                    for (let attr of attrs) {
                                                        const name = attr.name.toLowerCase();
                                                        if (name.includes('href') || name.includes('url') || name.includes('link')) {
                                                            const val = attr.value;
                                                            if (val && (val.startsWith('/') || val.startsWith('http'))) {
                                                                return val;
                                                            }
                                                        }
                                                    }
                                                }
                                                clickable = clickable.parentElement;
                                            }
                                            return null;
                                        }
                                    """)
                                    if url_from_click:
                                        if url_from_click.startswith("/"):
                                            event_url = f"https://www.volosports.com{url_from_click}"
                                        elif url_from_click.startswith("http"):
                                            event_url = url_from_click
                                        else:
                                            event_url = f"https://www.volosports.com/{url_from_click}"
                                except:
                                    pass
                            
                            # Strategy 6: Try clicking and intercepting navigation (last resort)
                            if not event_url:
                                try:
                                    # Set up a promise to capture navigation
                                    with page.expect_navigation(timeout=2000) as navigation_info:
                                        # Try clicking to see where it goes
                                        event.click()
                                    if navigation_info:
                                        event_url = navigation_info.value.url
                                        # Navigate back
                                        page.go_back()
                                        page.wait_for_timeout(1000)
                                except:
                                    # If navigation interception fails, try to get URL from current page after click
                                    try:
                                        original_url = page.url
                                        event.click()
                                        page.wait_for_timeout(1000)
                                        new_url = page.url
                                        if new_url != original_url and 'volosports.com' in new_url:
                                            event_url = new_url
                                            # Navigate back
                                            page.go_back()
                                            page.wait_for_timeout(1000)
                                    except:
                                        pass
                        except:
                            pass
                        
                        # Only store if we have a URL - we'll skip if we can't find one
                        if event_url:
                            # Extract concise title
                            title = event_text.split('\n')[0].strip() if '\n' in event_text else event_text
                            if len(title) > 80:
                                title = title[:80] + "..."
                            
                            matching_pickups.append({
                                'url': event_url,
                                'title': title
                            })
                            logger.info(f"    → URL: {event_url[:60]}...")
                        else:
                            logger.warning(f"    ⚠ Could not extract URL - will skip")
                    else:
                        logger.info(f"    → NOT free")
                        
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
            for i, pickup_info in enumerate(matching_pickups, 1):
                try:
                    if isinstance(pickup_info, dict):
                        title = pickup_info.get('title', 'N/A')
                        url = pickup_info.get('url', 'No URL (will click)')
                        logger.info(f"  {i}. {title[:100]}")
                        if url:
                            logger.info(f"      URL: {url}")
                    else:
                        # Legacy format
                        pickup_text = pickup_info.inner_text()[:200] if pickup_info.inner_text() else "N/A"
                        logger.info(f"  {i}. {pickup_text}")
                except:
                    logger.info(f"  {i}. [Could not extract text]")
            logger.info("=" * 60)
            
            # If search only mode, just log and return
            if self.search_only:
                logger.info("🔍 SEARCH ONLY MODE: Skipping actual signup")
                logger.info(f"Would sign up for {len(matching_pickups)} pickup(s) if not in search-only mode")
                return True
            
            # Sign up for each matching pickup using tabs
            # Process each pickup in a new tab to avoid navigation issues
            signed_up_count = 0
            context = page.context
            
            # Process each pickup by URL only (no elements to avoid detachment)
            for pickup_index, pickup_info in enumerate(matching_pickups, 1):
                # Extract pickup info - should always be a dict with url and title
                if not isinstance(pickup_info, dict):
                    logger.warning(f"Invalid pickup info format for pickup {pickup_index}, skipping")
                    continue
                
                pickup_title = pickup_info.get('title', f"pickup_{pickup_index}")
                pickup_url = pickup_info.get('url')
                
                if not pickup_url:
                    logger.warning(f"No URL for pickup {pickup_index} ({pickup_title[:80]}), skipping")
                    continue
                
                logger.info(f"Processing pickup {pickup_index}/{len(matching_pickups)}: {pickup_title}")
                
                pickup_page = None
                try:
                    # Always open in a new tab using the URL (no element clicking, no re-searching)
                    logger.info(f"Opening pickup URL in new tab: {pickup_url}")
                    pickup_page = context.new_page()
                    pickup_page.goto(pickup_url, wait_until='domcontentloaded', timeout=30000)
                    pickup_page.wait_for_timeout(3000)
                    
                    # Process this pickup page
                    success = self._process_single_pickup(pickup_page, pickup_title)
                    if success:
                        signed_up_count += 1
                        logger.info(f"✅ Successfully signed up for pickup #{signed_up_count}!")
                    
                except Exception as e:
                    logger.error(f"Error processing pickup {pickup_index}: {e}")
                finally:
                    # Always close the tab since we always open new tabs
                    if pickup_page and pickup_page != page:
                        try:
                            pickup_page.close()
                        except Exception as e:
                            logger.debug(f"Error closing tab: {e}")
            
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
    
    def _process_single_pickup(self, pickup_page, pickup_title):
        """Process a single pickup page - check registration, verify price, sign up"""
        try:
            # Check if already registered
            logger.info("Checking if already registered...")
            try:
                page_text = pickup_page.locator('body').inner_text().lower()
                already_registered_phrases = [
                    'you are already registered',
                    'already registered',
                    'you have already registered',
                    'view registration',
                    'already signed up',
                ]
                
                if any(phrase in page_text for phrase in already_registered_phrases):
                    logger.info("✓ Already registered for this pickup - skipping signup")
                    return False
            except Exception as e:
                logger.debug(f"Error checking registration status: {e}")
            
            # Verify Order Total is $0.00
            logger.info("Verifying Order Total is $0.00 on detail page...")
            order_total_is_zero = False
            
            try:
                page_text = pickup_page.locator('body').inner_text()
                import re
                
                order_total_pattern = r'order\s+total\s*:?\s*(\$[\d.]+)'
                match = re.search(order_total_pattern, page_text, re.IGNORECASE)
                
                if match:
                    price_found = match.group(1)
                    logger.info(f"Found Order Total: {price_found}")
                    
                    price_normalized = price_found.replace('.00', '').replace('.0', '')
                    if price_normalized == '$0':
                        order_total_is_zero = True
                        logger.info("✓ Order Total is $0.00 - verified!")
                    else:
                        order_total_is_zero = False
                        logger.info(f"✗ Order Total is NOT $0.00: {price_found}")
                else:
                    # Try alternative patterns
                    total_patterns = [
                        r'total\s*:?\s*(\$[\d.]+)',
                        r'order\s+total[^\$]*(\$[\d.]+)',
                    ]
                    total_match = None
                    for pattern in total_patterns:
                        total_match = re.search(pattern, page_text, re.IGNORECASE)
                        if total_match:
                            break
                    
                    if total_match:
                        price_found = total_match.group(1)
                        price_normalized = price_found.replace('.00', '').replace('.0', '')
                        if price_normalized == '$0':
                            order_total_is_zero = True
                            logger.info(f"✓ Order Total is $0.00 - verified! (found via alternative pattern)")
                        else:
                            order_total_is_zero = False
                            logger.info(f"✗ Order Total is NOT $0.00: {price_found}")
                    else:
                        logger.warning("Could not find 'Order Total' on page, assuming it's $0.00 (passed initial check)")
                        order_total_is_zero = True
                
                if not order_total_is_zero:
                    logger.warning("✗ Order Total is NOT $0.00 - skipping this pickup")
                    return False
                else:
                    logger.info("✓ Order Total verification passed - proceeding with signup")
                    
            except Exception as e:
                logger.warning(f"Error verifying Order Total: {e}")
                logger.info("Continuing with signup despite Order Total check error (passed initial check)...")
            
            # Find and check waiver checkboxes
            logger.info("Looking for waiver/agreement checkboxes...")
            waiver_checkboxes = []
            
            try:
                all_checkboxes = pickup_page.query_selector_all("input[type='checkbox']")
                
                for checkbox in all_checkboxes:
                    try:
                        if checkbox.is_checked():
                            continue
                        
                        is_waiver_checkbox = checkbox.evaluate("""
                            el => {
                                let current = el;
                                for (let i = 0; i < 5; i++) {
                                    if (!current || !current.parentElement) break;
                                    current = current.parentElement;
                                    const text = (current.innerText || '').toLowerCase();
                                    if (text.includes('waiver') || text.includes('agreement') || 
                                        text.includes('liability') || text.includes('code of conduct') ||
                                        text.includes('player code')) {
                                        return true;
                                    }
                                }
                                return false;
                            }
                        """)
                        
                        if is_waiver_checkbox:
                            waiver_checkboxes.append(checkbox)
                            if len(waiver_checkboxes) >= 2:
                                break
                    except:
                        pass
            except:
                pass
            
            # Fallback: use first 2 unchecked checkboxes
            if len(waiver_checkboxes) < 2:
                all_checkboxes = pickup_page.query_selector_all("input[type='checkbox']")
                for checkbox in all_checkboxes:
                    try:
                        if not checkbox.is_checked() and checkbox not in waiver_checkboxes:
                            waiver_checkboxes.append(checkbox)
                            if len(waiver_checkboxes) >= 2:
                                break
                    except:
                        pass
            
            logger.info(f"Found {len(waiver_checkboxes)} waiver/agreement checkbox(es)")
            
            # Check the checkboxes
            if len(waiver_checkboxes) >= 2:
                logger.info(f"Checking {len(waiver_checkboxes)} waiver checkbox(es)...")
                for i, checkbox in enumerate(waiver_checkboxes[:2], 1):
                    try:
                        checkbox.scroll_into_view_if_needed()
                        pickup_page.wait_for_timeout(300)
                        checkbox.click()
                        logger.info(f"✓ Checked checkbox {i}/2")
                        pickup_page.wait_for_timeout(500)
                    except Exception as e:
                        logger.warning(f"Could not check checkbox {i}: {e}")
            elif len(waiver_checkboxes) == 1:
                logger.info("Found 1 waiver checkbox, checking it...")
                try:
                    waiver_checkboxes[0].scroll_into_view_if_needed()
                    pickup_page.wait_for_timeout(300)
                    waiver_checkboxes[0].click()
                    logger.info("✓ Checked checkbox")
                    pickup_page.wait_for_timeout(500)
                except Exception as e:
                    logger.warning(f"Could not check checkbox: {e}")
            else:
                logger.warning(f"Expected 1-2 waiver checkboxes but found {len(waiver_checkboxes)}")
            
            # Wait for Register button to become enabled
            logger.info("Waiting for Register button to become enabled...")
            pickup_page.wait_for_timeout(1500)
            
            # Find and click Register button
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
                    register_button = pickup_page.wait_for_selector(selector, timeout=5000)
                    if register_button:
                        is_disabled = register_button.get_attribute('disabled')
                        if not is_disabled or is_disabled == 'false':
                            logger.info(f"Found enabled Register button using: {selector}")
                            break
                        else:
                            pickup_page.wait_for_timeout(2000)
                            is_disabled = register_button.get_attribute('disabled')
                            if not is_disabled or is_disabled == 'false':
                                break
                            register_button = None
                except:
                    continue
            
            if register_button:
                try:
                    register_button.scroll_into_view_if_needed()
                    pickup_page.wait_for_timeout(300)
                except:
                    pass
                register_button.click()
                logger.info("✓ Clicked Register button")
                pickup_page.wait_for_timeout(2000)
                
                # Check for confirmation dialogs
                try:
                    confirm_selectors = [
                        "button:has-text('Confirm')",
                        "button:has-text('Complete')",
                        "button[class*='confirm']",
                    ]
                    for selector in confirm_selectors:
                        try:
                            confirm_button = pickup_page.wait_for_selector(selector, timeout=3000)
                            if confirm_button:
                                confirm_button.click()
                                logger.info("✓ Confirmed registration")
                                break
                        except:
                            continue
                except Exception as e:
                    logger.info(f"No additional confirmation needed: {e}")
                
                return True
            else:
                logger.warning("Could not find enabled Register button")
                pickup_page.screenshot(path=f'register_button_not_found.png')
                return False
                
        except Exception as e:
            logger.error(f"Error processing pickup: {e}")
            pickup_page.screenshot(path=f'pickup_error.png')
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
                    login_success = self.login(page)
                    
                    if not login_success:
                        logger.error("❌ Login/Authentication failed - stopping execution")
                        if self.cookie:
                            logger.error("Please check your VOLO_COOKIE secret")
                        else:
                            logger.error("Please check your VOLO_EMAIL and VOLO_PASSWORD secrets")
                        page.screenshot(path='login_failed_final.png')
                        return
                    
                    logger.info("=" * 60)
                    logger.info("✅ AUTHENTICATION SUCCESSFUL!")
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
