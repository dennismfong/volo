# Testing the Volo Bot with GitHub Actions

Since you can't test locally, here's how to test using GitHub Actions:

## Quick Test (Manual Run)

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. Click **"Volo Sports Bot"** in the left sidebar
4. Click the **"Run workflow"** button (top right)
5. Click **"Run workflow"** again
6. The bot will run immediately!

## Viewing Test Results

1. Click on the workflow run that just started
2. You'll see it running in real-time
3. Click on **"Run Volo Bot"** step to see detailed logs
4. After it completes, check:
   - **Logs** - See what the bot found and did
   - **Artifacts** - Download logs and screenshots (if errors occurred)

## Controlling When It Runs

### Option 1: Manual Testing Only
- Don't set any schedule control secret
- Just use "Run workflow" button whenever you want to test
- The bot will still run automatically at 12:01 AM daily

### Option 2: Disable Scheduled Runs (Testing Mode)
1. Go to **Settings** → **Secrets and variables** → **Actions**
2. Add a new secret:
   - Name: `ENABLE_SCHEDULE`
   - Value: `false`
3. This disables the 12:01 AM scheduled runs
4. You can still manually trigger it anytime

### Option 3: Enable Scheduled Runs (Production Mode)
1. Either don't set `ENABLE_SCHEDULE` secret, OR
2. Set `ENABLE_SCHEDULE` to `true`
3. The bot will run automatically at 12:01 AM daily

## Understanding the Logs

When the bot runs, look for these log messages:

**Good signs:**
- ✅ "Login successful"
- ✅ "Found X matching pickup(s)"
- ✅ "Event matches criteria: 'Volleyball Pickup' and $0 total"
- ✅ "Successfully signed up for pickup #1!"

**Issues to watch for:**
- ❌ "Login may have failed" - Check your credentials
- ❌ "No matching pickups found" - Either no pickups available, or none match criteria
- ❌ "Could not find signup button" - Website structure may have changed

## Debugging Failed Runs

1. **Check the logs** - Look for error messages
2. **Download artifacts** - Screenshots are saved if errors occur
3. **Check selectors** - The website structure may have changed
4. **Verify credentials** - Make sure `VOLO_EMAIL` and `VOLO_PASSWORD` secrets are correct

## Testing Checklist

Before relying on the scheduled runs:

- [ ] Manual run completes successfully
- [ ] Bot can log in
- [ ] Bot finds volleyball pickups page
- [ ] Bot correctly filters for "Volleyball Pickup" events
- [ ] Bot correctly filters for $0 events
- [ ] Bot successfully signs up for matching events
- [ ] Logs show clear information about what it's doing

## Common Issues

**"No matching pickups found"**
- This is normal if there are no free volleyball pickups available
- Check the logs to see what events it found and why they were filtered out

**"Login failed"**
- Double-check your `VOLO_EMAIL` and `VOLO_PASSWORD` secrets
- Make sure they're set correctly in GitHub Secrets

**"Could not find signup button"**
- The Volo Sports website structure may have changed
- Check the screenshot artifact to see what the page looks like
- You may need to update the selectors in `volo_bot_github.py`
