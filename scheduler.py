#!/usr/bin/env python3
"""
Scheduler script that runs the Volo bot at 12:01am daily
Can be run as a daemon or scheduled via cron
"""

import schedule
import time
import logging
from datetime import datetime
from volo_bot import VoloBot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_bot():
    """Run the Volo bot"""
    try:
        bot = VoloBot()
        bot.run()
    except Exception as e:
        logger.error(f"Error running bot: {e}")


def main():
    """Main scheduler loop"""
    # Schedule the bot to run at 12:01am every day
    schedule.every().day.at("00:01").do(run_bot)
    
    logger.info("Volo Bot scheduler started")
    logger.info("Bot will run daily at 12:01am")
    logger.info("Press Ctrl+C to stop")
    
    # Run immediately if it's after midnight (for testing)
    current_time = datetime.now()
    if current_time.hour == 0 and current_time.minute <= 5:
        logger.info("Running bot immediately (it's just after midnight)")
        run_bot()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
