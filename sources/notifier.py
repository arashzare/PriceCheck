import os
import requests
from typing import List
from sources.models import Deal

def send_telegram_notification(deals: List[Deal], target_price_cad: float) -> bool:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return False

    header = f"🚨 *Huawei Watch Deal Alert (Canada Landed Cost)* 🚨\nTarget Threshold: *${target_price_cad:.2f} CAD*\n\n"
    items_text = []
    
    for d in deals:
        items_text.append(
            f"🏷️ *{d.model}* via *{d.store}*\n"
            f"💰 *Total Landed:* `${d.total_price_cad:.2f} CAD`\n"
            f"   (Item: `${d.item_price_cad:.2f}` + Shipping to CA: `${d.shipping_price_cad:.2f}`)\n"
            f"📌 *Condition:* {d.condition} | *Global:* {'✅ Yes' if d.is_global_version else '🔍 Check listing'}\n"
            f"🔗 [View & Buy on {d.store}]({d.url})\n"
        )

    message = header + "\n".join(items_text)
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"[Notifier] Telegram error: {e}")
        return False

def send_discord_notification(deals: List[Deal], target_price_cad: float) -> bool:
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        return False

    embeds = []
    for d in deals:
        embed = {
            "title": f"🎯 Deal: {d.model} (${d.total_price_cad:.2f} CAD)",
            "url": d.url,
            "description": f"**{d.title}**",
            "color": 3066993,  # Green
            "fields": [
                {"name": "🏪 Store", "value": d.store, "inline": True},
                {"name": "💵 Total Landed (CAD)", "value": f"**${d.total_price_cad:.2f}**", "inline": True},
                {"name": "📦 Shipping to Canada", "value": f"${d.shipping_price_cad:.2f} CAD", "inline": True},
                {"name": "🏷️ Item Price", "value": f"${d.item_price_cad:.2f} CAD", "inline": True},
                {"name": "🌍 Global Version", "value": "Yes" if d.is_global_version else "Check description", "inline": True},
                {"name": "✨ Condition", "value": d.condition, "inline": True}
            ],
            "footer": {"text": "Huawei Watch Blood Pressure Daily Deal Tracker"}
        }
        embeds.append(embed)

    payload = {
        "content": f"🚨 **Huawei Watch D2 / D3 Deal Alert!** Found items <= **${target_price_cad:.2f} CAD** (All shipping & fees included):",
        "embeds": embeds[:10]  # Discord allows up to 10 embeds per message
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        return resp.status_code in [200, 204]
    except Exception as e:
        print(f"[Notifier] Discord error: {e}")
        return False

def dispatch_notifications(deals: List[Deal], target_price_cad: float):
    if not deals:
        print(f"[Notifier] No deals found under ${target_price_cad:.2f} CAD today.")
        return

    print(f"\n==================== DEALS FOUND ({len(deals)}) ====================")
    for d in deals:
        print(d.summary())
        print("-" * 60)

    tg_sent = send_telegram_notification(deals, target_price_cad)
    if tg_sent:
        print("[Notifier] Successfully sent Telegram alert!")

    dc_sent = send_discord_notification(deals, target_price_cad)
    if dc_sent:
        print("[Notifier] Successfully sent Discord alert!")

    if not tg_sent and not dc_sent:
        print("[Notifier] Note: No TELEGRAM or DISCORD webhooks configured. Check environment variables or GitHub Secrets.")
