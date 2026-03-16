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
    
    def signup_for_volleyball(self, page):
        """Navigate to volleyball pickups and sign up"""
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
            
            # Find and click signup button
            signup_selectors = [
                "button:has-text('Sign Up')",
                "a:has-text('Sign Up')",
                "button[class*='signup']",
                "a[class*='signup']",
                "button[id*='signup']",
                "a[id*='signup']",
            ]
            
            signed_up = False
            for selector in signup_selectors:
                try:
                    page.click(selector, timeout=3000)
                    logger.info(f"Clicked signup button using: {selector}")
                    page.wait_for_timeout(2000)
                    signed_up = True
                    break
                except PlaywrightTimeoutError:
                    continue
            
            if not signed_up:
                logger.error("Could not find signup button")
                page.screenshot(path='signup_error.png')
                return False
            
            # Confirm signup if needed
            try:
                confirm_selectors = [
                    "button:has-text('Confirm')",
                    "button[class*='confirm']",
                ]
                for selector in confirm_selectors:
                    try:
                        page.click(selector, timeout=3000)
                        logger.info("Confirmed signup")
                        break
                    except PlaywrightTimeoutError:
                        continue
            except Exception as e:
                logger.info(f"No confirmation needed: {e}")
            
            logger.info("Successfully signed up for volleyball pickup!")
            return True
                
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
