# Quick GitHub Actions Setup Guide

This guide will help you deploy your Volo bot to GitHub Actions so it runs automatically at 12:01 AM daily - **completely free!**

## Step 1: Create GitHub Repository

1. Go to https://github.com and sign in (or create an account)
2. Click the "+" icon → "New repository"
3. Name it something like `volo-bot` (or whatever you prefer)
4. Make it **Public** (required for free GitHub Actions)
5. Click "Create repository"

## Step 2: Push Your Code to GitHub

In your terminal, run:

```bash
cd /Users/dennis.fong/volo

# Initialize git if not already done
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit: Volo Sports bot"

# Add your GitHub repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/volo-bot.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Add Secrets to GitHub

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

   **Secret 1:**
   - Name: `VOLO_EMAIL`
   - Value: Your Volo Sports email address

   **Secret 2:**
   - Name: `VOLO_PASSWORD`
   - Value: Your Volo Sports password

   **Secret 3 (Optional):**
   - Name: `VOLO_URL`
   - Value: `https://www.volosports.com` (or your specific URL)

   **Secret 4 (Optional):**
   - Name: `VOLO_VOLLEYBALL_URL`
   - Value: Direct URL to volleyball pickups page (if you know it)

## Step 4: Adjust Timezone (If Needed)

The workflow is set to run at **12:01 AM PST** (8:01 AM UTC).

To change the timezone:

1. Go to your repository → `.github/workflows/volo-bot.yml`
2. Edit the cron expression on line 9
3. Use this guide:
   - **PST (Pacific)**: `1 8 * * *` ← Current setting
   - **EST (Eastern)**: `1 5 * * *`
   - **CST (Central)**: `1 6 * * *`
   - **MST (Mountain)**: `1 7 * * *`
4. Commit the change

## Step 5: Test It!

1. Go to your repository → **Actions** tab
2. You should see "Volo Sports Bot" workflow
3. Click on it → **Run workflow** → **Run workflow**
4. This will manually trigger the bot to test if it works

## Step 6: Verify It's Scheduled

1. Go to **Actions** tab
2. Click on "Volo Sports Bot" workflow
3. You should see it's scheduled to run daily
4. Check the logs after it runs to make sure it worked

## That's It! 🎉

Your bot will now run automatically at 12:01 AM every day on GitHub's servers - **completely free!**

## Viewing Logs

- Go to **Actions** tab in your repository
- Click on any workflow run to see logs
- Logs and screenshots are saved as artifacts for 7 days

## Troubleshooting

**Bot doesn't run:**
- Check that the repository is **Public** (required for free Actions)
- Verify secrets are set correctly
- Check the Actions tab for error messages

**Login fails:**
- Double-check your email/password in Secrets
- The website structure may have changed - you may need to update selectors

**Can't find signup button:**
- Check the workflow run logs
- Screenshots are saved as artifacts if errors occur
- You may need to customize the selectors in `volo_bot_github.py`

## Manual Runs

You can manually trigger the bot anytime:
1. Go to **Actions** tab
2. Click "Volo Sports Bot"
3. Click "Run workflow" → "Run workflow"

## Privacy Note

Since the repository needs to be public for free Actions, be aware:
- Your code will be visible to others
- **Your secrets (email/password) are NOT visible** - they're encrypted
- Only you can see the workflow logs and secrets

If you want a private repository, you'll need GitHub Pro (paid), or use one of the other free options in `DEPLOYMENT.md`.
