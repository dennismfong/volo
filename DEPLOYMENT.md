# Free Deployment Options for Volo Bot

Since you don't want to keep your laptop running, here are several **free** options to deploy your bot:

## Option 1: GitHub Actions (Recommended) ⭐

**Pros:**
- Completely free for public repositories
- Very reliable (runs on GitHub's infrastructure)
- No credit card required
- Easy to set up
- Can run on a schedule

**Cons:**
- Repository must be public (or you need GitHub Pro)
- Limited to 2000 minutes/month for private repos (free tier)

### Setup Steps:

1. **Create a GitHub repository:**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/volo-bot.git
   git push -u origin main
   ```

2. **Add secrets to GitHub:**
   - Go to your repository → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `VOLO_EMAIL`: Your email
     - `VOLO_PASSWORD`: Your password
     - `VOLO_URL`: (Optional) Base URL
     - `VOLO_VOLLEYBALL_URL`: (Optional) Direct volleyball URL

3. **Adjust the schedule:**
   - Edit `.github/workflows/volo-bot.yml`
   - The cron expression `1 8 * * *` means 12:01 AM PST (8:01 AM UTC)
   - Adjust for your timezone:
     - PST (UTC-8): `1 8 * * *` (12:01 AM PST)
     - EST (UTC-5): `1 5 * * *` (12:01 AM EST)
     - CST (UTC-6): `1 6 * * *` (12:01 AM CST)

4. **The workflow will run automatically!**

**Note:** The GitHub Actions workflow uses Playwright (better for CI/CD). You can also modify it to use the Selenium version if needed.

---

## Option 2: PythonAnywhere

**Pros:**
- Free tier available
- Specifically designed for Python scheduled tasks
- Easy web interface

**Cons:**
- Free tier has limitations (can't run 24/7, limited CPU time)
- Tasks can only run once per day on free tier

### Setup Steps:

1. Sign up at https://www.pythonanywhere.com
2. Upload your code via the web interface or git
3. Set up a scheduled task:
   - Go to Tasks tab
   - Create a new scheduled task
   - Set time to 00:01 (12:01 AM)
   - Command: `python3 /home/YOUR_USERNAME/volo/volo_bot.py`
4. Add environment variables in the Files tab → `.env` file

---

## Option 3: Render

**Pros:**
- Free tier available
- Can run scheduled tasks
- Good documentation

**Cons:**
- Free tier services "spin down" after inactivity
- May need to use a workaround for scheduled tasks

### Setup Steps:

1. Sign up at https://render.com
2. Create a new "Background Worker"
3. Connect your GitHub repository
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `python3 scheduler.py`
6. Add environment variables in the dashboard

---

## Option 4: Railway

**Pros:**
- Free tier with $5 credit monthly
- Easy deployment
- Good for small projects

**Cons:**
- Limited free credits
- May need to upgrade if usage exceeds free tier

### Setup Steps:

1. Sign up at https://railway.app
2. Create a new project from GitHub
3. Add environment variables
4. Deploy and set up a cron job or use their scheduler

---

## Option 5: Replit

**Pros:**
- Free tier available
- Built-in cron jobs
- Easy to use

**Cons:**
- Free tier has limitations
- May require keeping the repl "awake"

### Setup Steps:

1. Sign up at https://replit.com
2. Create a new Python repl
3. Upload your code
4. Use Replit's built-in cron job feature
5. Set to run at 12:01 AM daily

---

## Option 6: AWS Lambda + EventBridge (Advanced)

**Pros:**
- Very reliable
- Free tier includes 1 million requests/month
- Scales automatically

**Cons:**
- More complex setup
- Selenium/Playwright needs special configuration for Lambda
- May need to use a headless browser service instead

### Setup Steps:

1. Create a Lambda function
2. Package your code (may need to use a headless browser service)
3. Set up EventBridge rule to trigger at 12:01 AM
4. Configure environment variables

---

## Recommendation

**For most users, GitHub Actions is the best choice** because:
- ✅ Completely free
- ✅ Very reliable
- ✅ No credit card needed
- ✅ Easy to set up
- ✅ Can manually trigger runs
- ✅ Logs and artifacts are saved

The workflow file (`.github/workflows/volo-bot.yml`) is already set up for you!

---

## Switching to Playwright Version

The GitHub Actions workflow uses Playwright which works better in CI environments. If you want to use the Playwright version locally too:

1. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```

2. Use `volo_bot_github.py` instead of `volo_bot.py`

Or update the GitHub Actions workflow to use the Selenium version if you prefer.

---

## Timezone Configuration

Make sure to adjust the cron schedule in the GitHub Actions workflow for your timezone:

- **PST (Pacific)**: `1 8 * * *` (12:01 AM PST = 8:01 AM UTC)
- **EST (Eastern)**: `1 5 * * *` (12:01 AM EST = 5:01 AM UTC)
- **CST (Central)**: `1 6 * * *` (12:01 AM CST = 6:01 AM UTC)
- **MST (Mountain)**: `1 7 * * *` (12:01 AM MST = 7:01 AM UTC)

You can use https://crontab.guru to help create the right cron expression.
