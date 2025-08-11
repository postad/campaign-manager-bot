import payload  # Ensure payload is imported to set environment variables
import os
import requests
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from bot_handlers import (start_handler, handle_main_menu, get_image, get_text, get_base_url, get_ppc, get_campaign_id,
                         get_channels, confirm_post, cancel, get_repost_campaign_id, handle_edit_options, editing_image, editing_text,
                         report_handler, remind_unposted_handler,
                         SELECTING_ACTION, GETTING_CAMPAIGN_ID, UPLOADING_IMAGE, GETTING_TEXT, GETTING_BASE_URL, GETTING_PPC,
                         GETTING_CHANNELS, CONFIRM_POST, GETTING_REPOST_CAMPAIGN_ID, EDIT_OPTIONS, EDITING_IMAGE, EDITING_TEXT)

def check_and_set_web_hook():
    bot_token = os.getenv("BOT_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")
    
    base_url = f"https://api.telegram.org/bot{bot_token}"

    # Get current webhook info
    response = requests.get(f"{base_url}/getWebhookInfo")
    data = response.json()

    current_url = data.get("result", {}).get("url", "")

    if current_url != webhook_url:
        set_response = requests.post(f"{base_url}/setWebhook", data={"url": webhook_url})
        if set_response.status_code == 200 and set_response.json().get("ok"):
            print(f"✅ Webhook set to {webhook_url}")
        else:
            print("❌ Failed to set webhook:", set_response.text)
    else:
        print(current_url)
        print("ℹ️ Webhook already set.")

def main():
    check_and_set_web_hook()
    token = os.getenv("BOT_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")

    if not token or not webhook_url:
        raise ValueError("BOT_TOKEN and WEBHOOK_URL environment variables must be set.")

    application = Application.builder().token(token).build()

    new_campaign_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.PHOTO, get_image)],
        states={
            GETTING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text)],
            GETTING_BASE_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_base_url)],
            GETTING_PPC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_ppc)],
            GETTING_CAMPAIGN_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_campaign_id)],
            GETTING_CHANNELS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_channels)],
            CONFIRM_POST: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_post)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={
            ConversationHandler.END: SELECTING_ACTION
        },
        per_message=True
    )

    repost_campaign_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, get_repost_campaign_id)],
        states={
            EDIT_OPTIONS: [CallbackQueryHandler(handle_edit_options)],
            EDITING_IMAGE: [MessageHandler(filters.PHOTO, editing_image)],
            EDITING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, editing_text)],
            GETTING_CHANNELS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_channels)],
            CONFIRM_POST: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_post)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        map_to_parent={
            ConversationHandler.END: SELECTING_ACTION
        },
        per_message=False
    )

    main_menu_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_handler)],
        states={
            SELECTING_ACTION: [CallbackQueryHandler(handle_main_menu)],
            UPLOADING_IMAGE: [new_campaign_handler],
            GETTING_REPOST_CAMPAIGN_ID: [repost_campaign_handler],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=False
    )

    application.add_handler(main_menu_handler)
    application.add_handler(CommandHandler("report", report_handler))
    application.add_handler(CommandHandler("remind_unposted", remind_unposted_handler))

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        url_path="/webhook",
        webhook_url=webhook_url
    )

if __name__ == "__main__":
    main()
    
