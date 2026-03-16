# How to Add Secrets to GitHub

If you can't find the "Secrets and variables" section, here are multiple ways to add secrets:

## Method 1: Direct URL (Easiest)

1. Replace `YOUR_USERNAME` and `REPO_NAME` in this URL:
   ```
   https://github.com/YOUR_USERNAME/REPO_NAME/settings/secrets/actions
   ```

2. For example, if your username is `dennis` and repo is `volo-bot`:
   ```
   https://github.com/dennis/volo-bot/settings/secrets/actions
   ```

3. Click **New repository secret** button

## Method 2: Via Repository Settings

1. Go to your repository on GitHub
2. Click the **Settings** tab (top navigation bar)
3. Look in the **left sidebar** for one of these:
   - **Secrets and variables** → **Actions**
   - **Security** → **Secrets and variables** → **Actions**
   - **Secrets** (might be directly visible)

4. If you still don't see it, you might need to:
   - Make sure you're the repository owner (or have admin access)
   - Make sure the repository exists and you're on the correct page
   - Try refreshing the page

## Method 3: Via Actions Workflow

1. Go to your repository → **Actions** tab
2. Click on "Volo Sports Bot" workflow
3. Click **Run workflow** button
4. If secrets are missing, GitHub might show a warning with a link to add them

## Method 4: Check Repository Permissions

If you still can't see secrets, you might not have the right permissions:

1. Go to **Settings** → **Collaborators** (or **Manage access**)
2. Make sure you're listed as an **Owner** or have **Admin** access
3. If it's an organization repository, you might need organization admin rights

## What Secrets to Add

Once you can access the secrets page, add these:

### Secret 1: VOLO_EMAIL
- **Name:** `VOLO_EMAIL`
- **Value:** Your Volo Sports email address

### Secret 2: VOLO_PASSWORD
- **Name:** `VOLO_PASSWORD`
- **Value:** Your Volo Sports password

### Secret 3: VOLO_URL (Optional)
- **Name:** `VOLO_URL`
- **Value:** `https://www.volosports.com`

### Secret 4: VOLO_VOLLEYBALL_URL (Optional)
- **Name:** `VOLO_VOLLEYBALL_URL`
- **Value:** Direct URL to volleyball pickups page (if you know it)

## Visual Guide

The secrets page should look like this:
```
Repository secrets
┌─────────────────────────────────────┐
│  New repository secret              │
├─────────────────────────────────────┤
│  Name: [________________]            │
│  Secret: [________________]        │
│  [Add secret]                      │
└─────────────────────────────────────┘
```

## Still Can't Find It?

1. **Make sure the repository is created** - You need to push code first
2. **Check you're logged in** - Make sure you're signed into GitHub
3. **Try a different browser** - Sometimes browser extensions can hide elements
4. **Check GitHub status** - Visit https://www.githubstatus.com to see if there are issues

## Alternative: Use Environment Variables in Workflow

If you absolutely can't access secrets (not recommended for passwords, but works for testing), you can temporarily hardcode values in the workflow file, but **this is insecure** and your credentials will be visible in the repository.

**Better solution:** If you're having persistent issues, try:
1. Creating a new repository
2. Making sure you're the owner
3. Using the direct URL method above
