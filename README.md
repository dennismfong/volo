# Volo Sports Volleyball Pickup Auto-Signup Bot

Automatically signs you up for Volo Sports volleyball pickups at 12:01am each day.

## 🚀 Free Deployment (No Laptop Required!)

**Don't want to keep your laptop running?** Deploy this bot for free using GitHub Actions!

👉 **See [GITHUB_SETUP.md](GITHUB_SETUP.md) for quick setup instructions**

Or check [DEPLOYMENT.md](DEPLOYMENT.md) for other free deployment options (PythonAnywhere, Render, Railway, etc.)

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install ChromeDriver

The bot uses Selenium with Chrome. You need ChromeDriver installed:

**macOS (using Homebrew):**
```bash
brew install chromedriver
```

**Or download manually:**
- Visit https://chromedriver.chromium.org/downloads
- Download the version matching your Chrome version
- Add to PATH or place in project directory

### 3. Configure Credentials

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Volo Sports email and password:
```
VOLO_EMAIL=your_email@example.com
VOLO_PASSWORD=your_password
```

**Optional:** If you know the direct URL to the volleyball pickups page, add it:
```
VOLO_VOLLEYBALL_URL=https://www.volosports.com/volleyball/pickups
```

### 4. Test the Bot

Run the bot manually first to make sure it works:

```bash
python volo_bot.py
```

**Note:** You may need to customize the selectors in `volo_bot.py` based on the actual Volo Sports website structure. The bot includes common selectors, but you may need to adjust them.

## Running the Bot

### Option 1: Using Python Scheduler (Recommended for Development)

Run the scheduler script:

```bash
python scheduler.py
```

This will keep running and execute the bot at 12:01am daily.

### Option 2: Using Cron (Recommended for Production)

Add a cron job to run at 12:01am daily:

```bash
crontab -e
```

Add this line (adjust the path to your project):
```
1 0 * * * cd /Users/dennis.fong/volo && /usr/bin/python3 volo_bot.py >> /Users/dennis.fong/volo/cron.log 2>&1
```

Or if you're using a virtual environment:
```
1 0 * * * cd /Users/dennis.fong/volo && /path/to/venv/bin/python volo_bot.py >> /Users/dennis.fong/volo/cron.log 2>&1
```

### Option 3: Using launchd (macOS)

Create a plist file for macOS launchd:

```bash
# Create the plist file
cat > ~/Library/LaunchAgents/com.volo.bot.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.volo.bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/dennis.fong/volo/volo_bot.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>0</integer>
        <key>Minute</key>
        <integer>1</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/dennis.fong/volo/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/dennis.fong/volo/launchd.error.log</string>
</dict>
</plist>
EOF

# Load the job
launchctl load ~/Library/LaunchAgents/com.volo.bot.plist
```

## Customization

The bot may need customization based on the actual Volo Sports website structure. Key areas to modify in `volo_bot.py`:

1. **Login selectors** - Update the selectors for email/password fields and login button
2. **Navigation** - Adjust how the bot navigates to volleyball pickups
3. **Signup button** - Update the selector for the signup button

### Finding the Right Selectors

1. Open the Volo Sports website in Chrome
2. Right-click on elements and select "Inspect"
3. Use the element's ID, class, or other attributes to create selectors
4. Update the selectors in `volo_bot.py`

### Debugging

To see the browser in action (for debugging), uncomment this line in `volo_bot.py`:
```python
# chrome_options.headless = False
```

The bot saves screenshots when errors occur (see `signup_error.png`).

## Logs

- Console output: Logs to console and `volo_bot.log`
- Cron logs: If using cron, check `cron.log`
- Launchd logs: If using launchd, check `launchd.log` and `launchd.error.log`

## Troubleshooting

1. **ChromeDriver issues**: Make sure ChromeDriver version matches your Chrome version
2. **Login fails**: Check your credentials in `.env` and verify the login selectors
3. **Can't find signup button**: The website structure may have changed - update selectors
4. **Bot runs but doesn't sign up**: Check the logs and screenshots for errors

## Security Notes

- Never commit your `.env` file to version control
- The `.env` file is already in `.gitignore`
- Consider using a dedicated account for the bot if possible

## License

This is a personal automation script. Use responsibly and in accordance with Volo Sports' terms of service.
