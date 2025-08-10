import os
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, ContextTypes
from database import Session, Campaign, Channel, ChannelGroup, CampaignPosting, Log
from sqlalchemy import func
from datetime import datetime, timedelta # Corrected: Added timedelta import
import decimal

# This import will ensure your bot doesn't crash on startup.
print("All libraries imported successfully.")

# Define conversation states
(SELECTING_ACTION, GETTING_CAMPAIGN_ID, UPLOADING_IMAGE, GETTING_TEXT, GETTING_BASE_URL, GETTING_PPC,
 GETTING_CHANNELS, CONFIRM_POST, GETTING_REPOST_CAMPAIGN_ID, EDIT_OPTIONS, EDITING_IMAGE, EDITING_TEXT) = range(12)

print("Conversation states defined.")

user_data_store = {}
OPERATOR_CHAT_ID = os.getenv("OPERATOR_CHAT_ID")

print(f"OPERATOR_CHAT_ID is set to: {OPERATOR_CHAT_ID}")

MESSAGES = {
    "start": "ברוך הבא, מנהל פלטפורמה. מה תרצה לעשות?",
    "new_campaign_image": "בבקשה העלה את התמונה לקמפיין החדש.",
    "new_campaign_text": "מעולה. עכשיו, בבקשה ספק את הטקסט לפוסט שלך.",
    "new_campaign_url": "בבקשה ספק את ה-URL הבסיסי לקמפיין.",
    "new_campaign_ppc": "מהו ה-PPC הכולל לקמפיין הזה?",
    "new_campaign_id": "לבסוף, ספק את מזהה הקמפיין (Campaign ID).",
    "repost_campaign_id": "בבקשה ספק את ה-Campaign ID של הקמפיין שברצונך לפרסם שוב.",
    "repost_preview": "הנה הקמפיין. האם תרצה להשתמש בו **כפי שהוא** או **לבצע שינויים**?",
    "editing_image": "בבקשה העלה את התמונה החדשה לקמפיין.",
    "editing_text": "כעת, בבקשה ספק את הטקסט החדש לפוסט.",
    "channels_select": "לאיזה ערוצים או קבוצות יש לפרסם את הקמפיין? אתה יכול לרשום שמות (לדוגמה: `חדשות, פיננסים`), שם קבוצה, או להקליד **all**.",
    "channels_not_found": "לא נמצאו ערוצים או קבוצות. בבקשה נסה שוב.",
    "confirm_post": "מוכן לפרסם את הקמפיין בערוצים הבאים:\n{channels_list}\n\nהשב עם **כן** לאישור.",
    "post_canceled": "❌ פרסום הקמפיין בוטל.",
    "post_success": "✅ הקמפיין פורסם בהצלחה!",
    "post_success_channels": "הקמפיין פורסם בערוצים הבאים:",
    "campaign_not_found": "Campaign ID לא נמצא. בבקשה נסה שוב.",
    "cancel_message": "❌ יצירת הקמפיין בוטלה.",
    "numeric_error": "הערך שהוזן אינו מספר חוקי. בבקשה ספק ערך מספרי.",
    "channel_owner_not_found": "לא ניתן למצוא את בעל הערוץ לפרסום."
}

print("MESSAGES dictionary loaded.")

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id == OPERATOR_CHAT_ID:
        keyboard = [
            [InlineKeyboardButton("קמפיין חדש", callback_data="new"), InlineKeyboardButton("פרסום מחדש", callback_data="repost")],
            [InlineKeyboardButton("דוח יומי", callback_data="report"), InlineKeyboardButton("תזכורות", callback_data="remind")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(MESSAGES["start"], reply_markup=reply_markup)
    else:
        await update.message.reply_text("שלום! אני בוט קמפיינים. בוט זה מיועד למנהלי פלטפורמה בלבד.")
    return SELECTING_ACTION

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if query.data == 'new':
        user_data_store[chat_id] = {'action': 'new'}
        await query.edit_message_text(MESSAGES["new_campaign_image"])
        return UPLOADING_IMAGE
    elif query.data == 'repost':
        user_data_store[chat_id] = {'action': 'repost'}
        await query.edit_message_text(MESSAGES["repost_campaign_id"])
        return GETTING_REPOST_CAMPAIGN_ID
    elif query.data == 'report':
        await report_handler(update, context)
        return ConversationHandler.END
    elif query.data == 'remind':
        await remind_unposted_handler(update, context)
        return ConversationHandler.END

async def get_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data_store[chat_id]['image_file_id'] = update.message.photo[-1].file_id
    await update.message.reply_text(MESSAGES["new_campaign_text"])
    return GETTING_TEXT

async def get_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data_store[chat_id]['text'] = update.message.text
    await update.message.reply_text(MESSAGES["new_campaign_url"])
    return GETTING_BASE_URL

async def get_base_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data_store[chat_id]['base_url'] = update.message.text
    await update.message.reply_text(MESSAGES["new_campaign_ppc"])
    return GETTING_PPC

async def get_ppc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    try:
        ppc_value = decimal.Decimal(update.message.text)
        user_data_store[chat_id]['total_campaign_ppc'] = ppc_value
        await update.message.reply_text(MESSAGES["new_campaign_id"])
        return GETTING_CAMPAIGN_ID
    except (ValueError, decimal.InvalidOperation):
        await update.message.reply_text(MESSAGES["numeric_error"])
        return GETTING_PPC

async def get_campaign_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data_store[chat_id]['campaign_id'] = update.message.text
    await update.message.reply_text(MESSAGES["channels_select"])
    return GETTING_CHANNELS

async def repost_campaign_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data_store[chat_id] = {'action': 'repost'}
    await update.message.reply_text(MESSAGES["repost_campaign_id"])
    return GETTING_REPOST_CAMPAIGN_ID

async def get_repost_campaign_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    campaign_id = update.message.text
    session = Session()
    campaign = session.query(Campaign).filter_by(campaign_id=campaign_id).first()
    if campaign:
        user_data_store[chat_id]['campaign_id'] = campaign_id
        user_data_store[chat_id]['image_file_id'] = campaign.image_file_id
        user_data_store[chat_id]['text'] = campaign.text
        user_data_store[chat_id]['base_url'] = campaign.base_url
        user_data_store[chat_id]['total_campaign_ppc'] = campaign.total_campaign_ppc
        
        keyboard = [
            [InlineKeyboardButton("כפי שהוא", callback_data="as_is"), InlineKeyboardButton("לבצע שינויים", callback_data="make_changes")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(MESSAGES["repost_preview"], reply_markup=reply_markup)
        return EDIT_OPTIONS
    else:
        await update.message.reply_text(MESSAGES["campaign_not_found"])
        return GETTING_REPOST_CAMPAIGN_ID

async def handle_edit_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    if query.data == 'as_is':
        await query.edit_message_text(MESSAGES["channels_select"])
        return GETTING_CHANNELS
    elif query.data == 'make_changes':
        await query.edit_message_text(MESSAGES["editing_image"])
        return EDITING_IMAGE

async def editing_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data_store[chat_id]['image_file_id'] = update.message.photo[-1].file_id
    await update.message.reply_text(MESSAGES["editing_text"])
    return EDITING_TEXT

async def editing_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data_store[chat_id]['text'] = update.message.text
    await update.message.reply_text(MESSAGES["channels_select"])
    return GETTING_CHANNELS

async def get_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    channels_input = update.message.text
    channels_list = [c.strip() for c in channels_input.split(',')]
    user_data_store[chat_id]['channels'] = channels_list

    session = Session()
    final_channels = []
    # Check for empty database and handle 'all' input
    if not session.query(Channel).first() and not session.query(ChannelGroup).first():
        await update.message.reply_text(MESSAGES["channels_not_found"])
        return GETTING_CHANNELS

    for item in channels_list:
        if item.lower() == 'all':
            final_channels.extend(session.query(Channel).all())
            break
        
        channel = session.query(Channel).filter_by(name=item).first()
        if channel:
            final_channels.append(channel)
        
        group = session.query(ChannelGroup).filter_by(group_name=item).first()
        if group:
            final_channels.extend(group.channels)
    
    if not final_channels:
        await update.message.reply_text(MESSAGES["channels_not_found"])
        return GETTING_CHANNELS

    user_data_store[chat_id]['final_channels'] = final_channels
    
    channels_display = "\n".join(set([c.name for c in final_channels]))
    await update.message.reply_text(MESSAGES["confirm_post"].format(channels_list=channels_display))
    return CONFIRM_POST

async def confirm_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() != 'כן':
        await update.message.reply_text(MESSAGES["post_canceled"])
        del user_data_store[update.effective_chat.id]
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    data = user_data_store[chat_id]
    session = Session()
    
    try:
        if data['action'] == 'new':
            existing_campaign = session.query(Campaign).filter_by(campaign_id=data['campaign_id']).first()
            if existing_campaign:
                await update.message.reply_text("❌ Campaign ID already exists. Please start a new campaign with a unique ID.")
                session.close()
                del user_data_store[chat_id]
                return ConversationHandler.END

            campaign = Campaign(
                image_file_id=data['image_file_id'],
                text=data['text'],
                base_url=data['base_url'],
                campaign_id=data['campaign_id'],
                total_campaign_ppc=data['total_campaign_ppc']
            )
            session.add(campaign)
            session.commit()
        else:
            campaign = session.query(Campaign).filter_by(campaign_id=data['campaign_id']).first()
            if not campaign:
                await update.message.reply_text(MESSAGES["campaign_not_found"])
                session.close()
                del user_data_store[chat_id]
                return ConversationHandler.END
                
            if 'image_file_id' in data and 'text' in data: 
                campaign.image_file_id = data['image_file_id']
                campaign.text = data['text']
            session.commit()
    except Exception as e:
        await update.message.reply_text(f"❌ An error occurred while saving the campaign: {e}")
        session.rollback()
        session.close()
        del user_data_store[chat_id]
        return ConversationHandler.END

    posted_channels = []
    for channel in set(data['final_channels']):
        try:
            group = session.query(ChannelGroup).join(ChannelGroup.channels).filter(Channel.id == channel.id).first()
            if not group:
                await update.message.reply_text(MESSAGES["channel_owner_not_found"])
                continue

            total_ppc = campaign.total_campaign_ppc
            ppc_percentage = group.ppc_percentage
            individual_ppc = total_ppc * (ppc_percentage / 100)
            
            unique_url = f"{campaign.base_url}{campaign.campaign_id}/{channel.name}"
            caption = f"{campaign.text}\n\nתשלום PPC: {individual_ppc}\n{unique_url}"

            if channel.is_bot_admin:
                await context.bot.send_photo(chat_id=channel.telegram_chat_id, photo=campaign.image_file_id, caption=caption)
                posting = CampaignPosting(campaign_id=campaign.id, channel_id=channel.id, status='posted_automatically', posted_at=datetime.utcnow())
                session.add(posting)
                session.commit()
                posted_channels.append(channel.name)
            else:
                if not channel.channel_owner_contact_id:
                    await update.message.reply_text(f"❌ Cannot post to {channel.name}: owner contact ID is missing.")
                    continue

                message = await context.bot.send_photo(chat_id=channel.channel_owner_contact_id, photo=campaign.image_file_id, caption=caption)
                posting = CampaignPosting(campaign_id=campaign.id, channel_id=channel.id, status='sent_to_owner', sent_at=datetime.utcnow(), message_id=message.message_id)
                session.add(posting)
                session.commit()
                posted_channels.append(channel.name)

        except Exception as e:
            print(f"Failed to post to {channel.name}: {e}")
            await update.message.reply_text(f"❌ Failed to post to {channel.name}: {e}")
    
    await update.message.reply_text(f"{MESSAGES['post_success']}\n{MESSAGES['post_success_channels']}\n" + "\n".join(posted_channels))
    session.close()
    del user_data_store[chat_id]
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MESSAGES["cancel_message"])
    if update.effective_chat.id in user_data_store:
        del user_data_store[update.effective_chat.id]
    return ConversationHandler.END

# Placeholder handlers
async def report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Generating daily report...")

async def remind_unposted_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sending reminders for unposted campaigns...")

# Scheduled Task for Message Deletion
async def delete_old_messages(context: ContextTypes.DEFAULT_TYPE):
    session = Session()
    try:
        yesterday = datetime.utcnow() - timedelta(days=1)
        posts_to_delete = session.query(CampaignPosting).filter(
            CampaignPosting.status == 'sent_to_owner',
            CampaignPosting.sent_at < yesterday
        ).all()
        
        for post in posts_to_delete:
            try:
                owner_chat_id = session.query(Channel.channel_owner_contact_id).filter_by(id=post.channel_id).scalar()
                if owner_chat_id:
                    await context.bot.delete_message(chat_id=owner_chat_id, message_id=post.message_id)
                    post.status = 'deleted'
                else:
                    print(f"Owner chat ID not found for channel {post.channel_id}. Skipping deletion.")
                session.commit()
            except Exception as e:
                print(f"Failed to delete message {post.message_id}: {e}")
                session.rollback()
    except Exception as e:
        print(f"An error occurred in delete_old_messages: {e}")
    finally:
        session.close()

print("End of file.")
