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
                                logger.info(f"  → Price: {', '.join(non_zero_prices)} (NOT free)")
                            elif any(p in ['$0', '$0.00', '$0.0'] for p in price_matches):
                                # Only $0 prices found
                                has_free_price = True
                                logger.info("  → Price: $0 (FREE)")
                            else:
                                # Has price patterns but unclear - be conservative
                                has_free_price = False
                                logger.info(f"  → Price patterns: {price_matches} (assuming NOT free)")
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
                                            logger.info(f"  Found price in div: {div_prices}")
                                            
                                            non_zero = [p for p in div_prices if p not in ['$0', '$0.00', '$0.0']]
                                            if non_zero:
                                                has_free_price = False
                                                logger.info(f"  → Div has non-zero price: {non_zero}")
                                                break
                                            elif any(p in ['$0', '$0.00', '$0.0'] for p in div_prices):
                                                has_free_price = True
                                                logger.info(f"  → Div has $0 price")
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
                                                    logger.info(f"  Found price element: '{price_text}'")
                                                    
                                                    # Check for price patterns
                                                    elem_price_matches = re.findall(r'\$[\d.]+', price_text)
                                                    if elem_price_matches:
                                                        non_zero = [p for p in elem_price_matches if p not in ['$0', '$0.00', '$0.0']]
                                                        if non_zero:
                                                            has_free_price = False
                                                            logger.info(f"  → Price element has non-zero price: {non_zero}")
                                                            break
                                                        elif any(p in ['$0', '$0.00', '$0.0'] for p in elem_price_matches):
                                                            has_free_price = True
                                                            logger.info(f"  → Price element is $0")
                                                            break
                                            if has_price_element:
                                                break
                                    except:
                                        continue
                            
                            # If still no price found, it's FREE
                            if not has_price_element:
                                has_free_price = True
                                logger.info("  → No price element or price pattern found in any div - event is FREE")
                    
                    except Exception as e:
                        logger.warning(f"  Error checking price: {e}")
                        # If we can't determine, be conservative and assume it's not free
                        has_free_price = False
                        found_price_value = "error checking"
                    
                    if has_free_price:
                        logger.info("✓ Event matches criteria: 'Volleyball Pickup' and $0/free")
                        matching_pickups.append(event)
                    else:
                        price_info = found_price_value or "has price (not $0)"
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
            # Use a while loop so we can re-find pickups when elements become stale
            signed_up_count = 0
            pickup_index = 0
            max_attempts = len(matching_pickups) * 2  # Safety limit
            attempts = 0
            
            while pickup_index < len(matching_pickups) and attempts < max_attempts:
                attempts += 1
                try:
                    pickup = matching_pickups[pickup_index]
                    logger.info(f"Attempting to sign up for pickup {pickup_index + 1}/{len(matching_pickups)}...")
                    
                    # Click on the pickup card/event to go to detail page
                    try:
                        logger.info("Clicking on event to view details...")
                        # Scroll into view first
                        pickup.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)
                        pickup.click()
                        page.wait_for_timeout(3000)  # Wait for detail page to load
                    except Exception as e:
                        logger.warning(f"Could not click pickup: {e}")
                        # If element is detached, navigate back and re-find pickups
                        if "not attached" in str(e).lower() or "detached" in str(e).lower():
                            logger.info("Element detached - navigating back and re-finding pickups...")
                            try:
                                volleyball_url = os.getenv('VOLO_VOLLEYBALL_URL', 
                                    'https://www.volosports.com/discover?cityName=San%20Francisco&subView=DAILY&view=SPORTS&sportNames%5B0%5D=Volleyball')
                                page.goto(volleyball_url, wait_until='domcontentloaded', timeout=15000)
                                page.wait_for_timeout(3000)
                                logger.info("✓ Returned to pickups page")
                                
                                # Re-find matching pickups since element references are stale
                                matching_pickups = self.find_matching_pickups(page)
                                if matching_pickups:
                                    logger.info(f"Re-found {len(matching_pickups)} matching pickups")
                                    # Break out of inner loop to restart with new elements
                                    break
                                else:
                                    logger.warning("No matching pickups found after re-finding")
                                    break
                            except Exception as nav_error:
                                logger.warning(f"Could not navigate back: {nav_error}")
                                # Try go_back as fallback
                                try:
                                    page.go_back()
                                    page.wait_for_timeout(2000)
                                    matching_pickups = self.find_matching_pickups(page)
                                    if matching_pickups:
                                        logger.info(f"Re-found {len(matching_pickups)} matching pickups")
                                        break
                                except:
                                    pass
                        continue
                    
                    # FIRST: Check if already registered - skip if so
                    logger.info("Checking if already registered...")
                    try:
                        page_text = page.locator('body').inner_text().lower()
                        already_registered_phrases = [
                            'you are already registered',
                            'already registered',
                            'you have already registered',
                            'view registration',
                            'already signed up',
                        ]
                        
                        is_already_registered = any(phrase in page_text for phrase in already_registered_phrases)
                        
                        if is_already_registered:
                            logger.info("✓ Already registered for this pickup - skipping signup")
                            # Navigate back to pickups page and re-find pickups for next signup
                            logger.info("Navigating back to pickups page...")
                            try:
                                volleyball_url = os.getenv('VOLO_VOLLEYBALL_URL', 
                                    'https://www.volosports.com/discover?cityName=San%20Francisco&subView=DAILY&view=SPORTS&sportNames%5B0%5D=Volleyball')
                                page.goto(volleyball_url, wait_until='domcontentloaded', timeout=15000)
                                page.wait_for_timeout(3000)  # Wait for page to fully load
                                logger.info("✓ Returned to pickups page")
                                
                                # Re-find matching pickups since element references are now stale
                                logger.info("Re-finding matching pickups after navigation...")
                                matching_pickups = self.find_matching_pickups(page)
                                if matching_pickups:
                                    logger.info(f"Re-found {len(matching_pickups)} matching pickups")
                                    # Continue with the loop, but we need to break and restart since we have new elements
                                    # Actually, we can't easily restart the loop, so we'll just continue
                                    # The next iteration will try to click, and if it fails, we'll handle it
                                else:
                                    logger.warning("No matching pickups found after navigation")
                            except:
                                try:
                                    page.go_back()
                                    page.wait_for_timeout(2000)
                                    # Re-find matching pickups
                                    matching_pickups = self.find_matching_pickups(page)
                                    if matching_pickups:
                                        logger.info(f"Re-found {len(matching_pickups)} matching pickups")
                                except:
                                    pass
                            continue  # Skip to next pickup
                    except Exception as e:
                        logger.debug(f"Error checking registration status: {e}")
                    
                    # SECOND CHECK: Verify "Order Total" is $0.00 on the detail page
                    # This is a safety check in case price didn't show on the list page
                    logger.info("Verifying Order Total is $0.00 on detail page...")
                    order_total_is_zero = False
                    
                    try:
                        # Get the page text and search for "Order Total"
                        # Use body element to get all text
                        page_text = page.locator('body').inner_text()
                        import re
                        
                        # Look for "Order Total" followed by a price
                        # Pattern: "Order Total" (optional colon/whitespace) then $X.XX or $X
                        order_total_pattern = r'order\s+total\s*:?\s*(\$[\d.]+)'
                        match = re.search(order_total_pattern, page_text, re.IGNORECASE)
                        
                        if match:
                            price_found = match.group(1)
                            logger.info(f"Found Order Total: {price_found}")
                            
                            # Check if it's $0.00 (normalize formats)
                            price_normalized = price_found.replace('.00', '').replace('.0', '')
                            if price_normalized == '$0':
                                order_total_is_zero = True
                                logger.info("✓ Order Total is $0.00 - verified!")
                            else:
                                order_total_is_zero = False
                                logger.info(f"✗ Order Total is NOT $0.00: {price_found}")
                        else:
                            # Order Total text not found - might be in different format
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
                                # Could not find Order Total - log warning but continue
                                logger.warning("Could not find 'Order Total' on page, assuming it's $0.00 (passed initial check)")
                                order_total_is_zero = True  # Assume it's free since it passed initial check
                                all_prices = re.findall(r'\$[\d.]+', page_text)
                                if all_prices:
                                    # There are prices but none near "total" - might be free
                                    logger.info(f"Found prices on page but none near 'total': {all_prices}")
                                    # Check if any are $0
                                    if any(p in ['$0', '$0.00', '$0.0'] for p in all_prices):
                                        order_total_is_zero = True
                                        logger.info("✓ Found $0.00 on page - assuming it's the order total")
                                    else:
                                        # Has prices but not $0 - might not be free
                                        logger.warning("Found prices on page but none are $0 - being cautious")
                                        order_total_is_zero = False
                                else:
                                    # No prices found at all - likely free
                                    order_total_is_zero = True
                                    logger.info("No prices found on page - assuming Order Total is $0.00")
                        
                        if not order_total_is_zero:
                            logger.warning("✗ Order Total is NOT $0.00 - skipping this pickup")
                            # Go back to the list page
                            try:
                                page.go_back()
                                page.wait_for_timeout(2000)
                            except:
                                pass
                            continue
                        else:
                            logger.info("✓ Order Total verification passed - proceeding with signup")
                        
                    except Exception as e:
                        logger.warning(f"Error verifying Order Total: {e}")
                        # If verification fails, continue anyway (since it passed initial check)
                        logger.info("Continuing with signup despite Order Total check error (passed initial check)...")
                    
                    # On the detail page, we need to:
                    # 1. Check both waiver/agreement checkboxes
                    # 2. Wait for Register button to become enabled
                    # 3. Click Register button
                    
                    try:
                        # Find and check the waiver/agreement checkboxes
                        logger.info("Looking for waiver/agreement checkboxes...")
                        
                        # Try to find checkboxes within waiver/agreement sections first
                        # Look for checkboxes near text containing "waiver", "agreement", "liability", etc.
                        waiver_checkboxes = []
                        
                        # Strategy 1: Find checkboxes near waiver-related text using locators
                        try:
                            # Find all checkboxes first
                            all_checkboxes = page.query_selector_all("input[type='checkbox']")
                            
                            # For each checkbox, check if it's near waiver text
                            for checkbox in all_checkboxes:
                                try:
                                    if checkbox.is_checked():
                                        continue
                                    
                                    # Get the checkbox's parent container text
                                    # Use evaluate to check if parent contains waiver text
                                    is_waiver_checkbox = checkbox.evaluate("""
                                        el => {
                                            // Walk up to find parent with text
                                            let current = el;
                                            for (let i = 0; i < 5; i++) {
                                                if (!current || !current.parentElement) break;
                                                current = current.parentElement;
                                                const text = (current.innerText || '').toLowerCase();
                                                // Check if this container has waiver-related text
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
                        
                        # Strategy 2: Fallback - if still not enough, use first 2 unchecked checkboxes
                        if len(waiver_checkboxes) < 2:
                            all_checkboxes = page.query_selector_all("input[type='checkbox']")
                            for checkbox in all_checkboxes:
                                try:
                                    if not checkbox.is_checked() and checkbox not in waiver_checkboxes:
                                        waiver_checkboxes.append(checkbox)
                                        if len(waiver_checkboxes) >= 2:
                                            break
                                except:
                                    pass
                        
                        logger.info(f"Found {len(waiver_checkboxes)} waiver/agreement checkbox(es)")
                        
                        # We need exactly 2 checkboxes (waiver/agreement)
                        if len(waiver_checkboxes) >= 2:
                            logger.info(f"Checking {len(waiver_checkboxes)} waiver checkbox(es)...")
                            for i, checkbox in enumerate(waiver_checkboxes[:2], 1):  # Check first 2
                                try:
                                    # Scroll checkbox into view first
                                    checkbox.scroll_into_view_if_needed()
                                    page.wait_for_timeout(300)
                                    # Use click for better reliability
                                    checkbox.click()
                                    logger.info(f"✓ Checked checkbox {i}/2")
                                    page.wait_for_timeout(500)  # Small delay between checks
                                except Exception as e:
                                    logger.warning(f"Could not check checkbox {i}: {e}")
                        elif len(waiver_checkboxes) == 1:
                            logger.info("Found 1 waiver checkbox, checking it...")
                            try:
                                waiver_checkboxes[0].scroll_into_view_if_needed()
                                page.wait_for_timeout(300)
                                waiver_checkboxes[0].click()
                                logger.info("✓ Checked checkbox")
                                page.wait_for_timeout(500)
                            except Exception as e:
                                logger.warning(f"Could not check checkbox: {e}")
                        else:
                            logger.warning(f"Expected 1-2 waiver checkboxes but found {len(waiver_checkboxes)}")
                        
                        # Wait for Register button to become enabled after checking boxes
                        logger.info("Waiting for Register button to become enabled...")
                        page.wait_for_timeout(1500)  # Give time for button to enable
                        
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
                            # Scroll button into view if not already
                            try:
                                register_button.scroll_into_view_if_needed()
                                page.wait_for_timeout(300)
                            except:
                                pass
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
                            
                            # Navigate back to pickups page to continue with next pickup
                            # Only if there are more pickups to sign up for
                            if pickup_index + 1 < len(matching_pickups):
                                logger.info("Navigating back to pickups page for next signup...")
                                try:
                                    # Get the volleyball URL from environment or use default
                                    volleyball_url = os.getenv('VOLO_VOLLEYBALL_URL', 
                                        'https://www.volosports.com/discover?cityName=San%20Francisco&subView=DAILY&view=SPORTS&sportNames%5B0%5D=Volleyball')
                                    page.goto(volleyball_url, wait_until='domcontentloaded', timeout=15000)
                                    page.wait_for_timeout(3000)  # Wait for page to fully load
                                    logger.info("✓ Returned to pickups page")
                                    
                                    # Re-find matching pickups since element references are now stale
                                    logger.info("Re-finding matching pickups after navigation...")
                                    matching_pickups = self.find_matching_pickups(page)
                                    if matching_pickups:
                                        logger.info(f"Re-found {len(matching_pickups)} matching pickups")
                                        # Reset pickup_index to current position (or 0 if we want to restart)
                                        # Since we already processed pickup_index, we can continue from there
                                        # But we need to make sure we don't skip any
                                        pickup_index = 0  # Restart from beginning with fresh elements
                                    else:
                                        logger.warning("No matching pickups found after navigation")
                                        break
                                except Exception as e:
                                    logger.warning(f"Could not navigate back to pickups page: {e}")
                                    # Try go_back as fallback
                                    try:
                                        page.go_back()
                                        page.wait_for_timeout(2000)
                                        # Re-find matching pickups
                                        matching_pickups = self.find_matching_pickups(page)
                                        if matching_pickups:
                                            logger.info(f"Re-found {len(matching_pickups)} matching pickups")
                                            pickup_index = 0
                                        else:
                                            break
                                    except:
                                        break
                            
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
