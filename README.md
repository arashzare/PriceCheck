# 🩺 Huawei Watch D2 / D3 Daily Price & Deal Tracker (Canada)

An automated daily price tracking system that monitors global prices for the **Huawei Watch D2** and **Huawei Watch D3** (smartwatches with medical-grade inflatable cuff blood pressure monitoring).

It computes the **total landed cost to Canada** (Item Price + Shipping to Canada + Currency conversion to CAD) and sends automated push alerts (Discord or Telegram) whenever the price drops to or below your target (e.g. **~$400 CAD**).

---

## 🚀 Key Features

- 🇨🇦 **True Landed Cost:** Automatically extracts and includes **shipping costs to Canada** and normalizes all currencies (USD, EUR, GBP) into **CAD**.
- 🔍 **Watches Monitored:** Tracks both **Huawei Watch D2** and **Huawei Watch D3** Global versions.
- 🛡️ **Anti-False-Positive Filters:** Filters out replacement straps, screen protectors, cases, and wristbands so only complete smartwatches trigger alerts.
- ⏰ **Zero-Cost Daily Automation:** Runs completely free via **GitHub Actions** every day at 8:00 AM EDT (12:00 UTC) without requiring your PC to be on.
- 📲 **Instant Alerts:** Sends rich notifications to **Telegram** or **Discord** with clickable buy links and price breakdowns.

---

## 📁 Project Structure

```text
├── .github/
│   └── workflows/
│       └── price_tracker.yml    # Daily GitHub Actions cron workflow
├── sources/
│   ├── amazon.py                # Amazon Canada & Amazon Global scraper (Playwright)
│   ├── ebay.py                  # eBay Canada / Global tracker (Shipping to CA included)
│   ├── importers.py             # Specialty importers (WondaMobile, Giztop)
│   ├── currency.py              # Real-time exchange rate converter to CAD
│   ├── notifier.py              # Discord & Telegram alert dispatchers
│   └── models.py                # Data classes for deals and pricing
├── tracker.py                   # Main runner script
└── requirements.txt             # Dependencies
```

---

## ⚙️ Step-by-Step Setup Guide

### 1. Push to a Private GitHub Repository
1. Create a new repository on [GitHub](https://github.com/new) (select **Private**).
2. In this folder on your computer, push the code:
   ```bash
   git add .
   git commit -m "Add Huawei Watch D2/D3 price tracker"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   git branch -M main
   git push -u origin main
   ```

---

### 2. Configure Notifications (Choose Discord or Telegram)

#### Option A: Discord Webhook (Easiest, 1 minute)
1. In your Discord server, right-click any channel -> **Edit Channel** -> **Integrations** -> **Webhooks**.
2. Click **New Webhook** and copy the **Webhook URL**.

#### Option B: Telegram Bot
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot`, choose a name and username, and copy the **HTTP API Token**.
3. Start a chat with your new bot (send `/start`).
4. Find your Chat ID by messaging `@userinfobot` or `@RawDataBot`.

---

### 3. Add GitHub Secrets
In your GitHub repository:
1. Go to **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret**.
2. Add the following secrets:

| Secret Name | Value Description | Example |
| :--- | :--- | :--- |
| `TARGET_PRICE_CAD` | Target max landed price in CAD (Item + Shipping) | `420.0` |
| `DISCORD_WEBHOOK_URL` | *(Optional)* Your Discord Webhook URL | `https://discord.com/api/webhooks/...` |
| `TELEGRAM_BOT_TOKEN` | *(Optional)* Your Telegram bot token | `123456789:ABC...` |
| `TELEGRAM_CHAT_ID` | *(Optional)* Your Telegram numerical chat ID | `987654321` |

---

### 4. Test Run on GitHub Actions
1. In your repository, click the **Actions** tab at the top.
2. Select **Daily Huawei Watch D2 & D3 Price Tracker** from the left sidebar.
3. Click **Run workflow** -> **Run workflow**.
4. The job will run and send you an alert if matching deals are found. It will also attach a `daily-deals-report` artifact.

---

## 💻 Running Locally (Optional)

If you want to run or test the script on your computer:

```bash
# 1. Install dependencies & browser
pip install -r requirements.txt
playwright install chromium

# 2. (Optional) Set your environment variables
set TARGET_PRICE_CAD=420.0
set DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# 3. Run the tracker
python tracker.py
```
