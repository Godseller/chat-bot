import requests
import numpy as np
import re
import os

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes, CallbackQueryHandler

load_dotenv()
FAST_API_HOST = os.environ['FAST_API_HOST']
FAST_API_PORT = os.environ['FAST_API_PORT']
TELEGRAM_BOT_KEY = os.environ['TELEGRAM_BOT_KEY']

CHOICE, FAQ, ATM, CURRENCY, DEFAULT_EXCHANGE, CURRENCY_FROM, CURRENCY_TO, EXCHANGE_WAY = range(8)

EXCHANGE_AIM = [["BYN", "Конверсия"]]
EXCHANGE_CHOICE_WAY = [['Цифровой банк', 'По карточке', 'Наличные']]
CURRENCY_AVAILABLE = [['USD', 'EUR', 'RUB']]

async def start(update, context):
    keyboard = [
        [InlineKeyboardButton("FAQ", callback_data="faq")],
        [InlineKeyboardButton("Ближайший банкомат", callback_data="atm")],
        [InlineKeyboardButton("Курсы валют", callback_data="exchange")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Вас приветствует чат-бот Приорбанка!\nПожалуйста, выберите интересующую Вас функцию:",
        reply_markup=reply_markup
    )
    return CHOICE

async def process_choice(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == 'faq':
        await query.message.reply_text("Задайте вопрос:")
        return FAQ
    if data == 'atm':
        await query.message.reply_text("Укажите адрес, по которому Вы находитесь:")
        return ATM
    if data == 'exchange':
        await query.message.reply_text(
            "Просим указать дополнительные параметры.\n"
            "Введите команду /cancel, чтобы прекратить разговор.\n\n"
            "Пожалуйста, выберите валюту продажи:",
            reply_markup=ReplyKeyboardMarkup(
                EXCHANGE_AIM, one_time_keyboard=True
            ),
        )
        return DEFAULT_EXCHANGE

def handle_response(text: str):
    user_message = text.lower()
    response = requests.get(f'http://{FAST_API_HOST}:{FAST_API_PORT}/respond_on_question/{user_message}')
    return response.text

async def faq_response(update, context):
    text = update.message.text
    response = handle_response(text)
    await update.message.reply_text(response)
    return ConversationHandler.END

async def closest_atm(update, context):
    location_text = update.message.text
    link = f"http://{FAST_API_HOST}:{FAST_API_PORT}/find"
    atm_info = requests.post(url=link, json={'address': location_text})
    await update.message.reply_text(f"Ближайший банкомат:\n{atm_info.text}")
    return ConversationHandler.END

# async def currency_exchange(update, context):
#     await update.message.reply_text(
#         "Для более точного ответа необходимо ответить на дополнительные вопросы.\n"
#         "Команда /cancel, чтобы прекратить разговор.\n\n"
#         "Пожалуйста, выберите интересующий обмен.",
#         reply_markup=ReplyKeyboardMarkup(
#             EXCHANGE_AIM, one_time_keyboard=True
#         ),
#     )
#     return DEFAULT_EXCHANGE

async def default_exchange_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    way_input = update.message.text
    result = ConversationHandler.END
    if way_input == EXCHANGE_AIM[0][0]:
        context.user_data["BYN"] = 1
        await update.message.reply_text(
            "Пожалуйста, выберите валюту.",
            reply_markup=ReplyKeyboardMarkup(
                CURRENCY_AVAILABLE, one_time_keyboard=True
            ),
        )
        result = CURRENCY_TO
    elif way_input == EXCHANGE_AIM[0][1]:
        context.user_data["BYN"] = 0
        await update.message.reply_text(
            "Пожалуйста, выберите имеющуюся валюту.",
            reply_markup=ReplyKeyboardMarkup(
                CURRENCY_AVAILABLE, one_time_keyboard=True
            ),
        )
        result = CURRENCY_FROM
    else:
        await update.message.reply_text(
            "Неверные данные, пожалуйста, попробуйте снова.",
            reply_markup=ReplyKeyboardRemove(),
        )
        result = ConversationHandler.END

    return result


async def currency_from_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currency_from_input = np.array(re.findall(r'\w+', update.message.text))
    result = CURRENCY_TO
    if not np.isin(currency_from_input, CURRENCY_AVAILABLE).all:
        await update.message.reply_text(
            "Неверные данные, пожалуйста, попробуйте снова.",
            reply_markup=ReplyKeyboardRemove(),
        )
        result = ConversationHandler.END
    else:
        context.user_data["currency_from"] = currency_from_input
        await update.message.reply_text(
            "Выберите валюту покупки:",
            reply_markup=ReplyKeyboardMarkup(
                CURRENCY_AVAILABLE, one_time_keyboard=True
            ),
        )
    return result


async def currency_to_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    currency_to_input = np.array(re.findall(r'\w+', update.message.text))
    result = EXCHANGE_WAY
    if not np.isin(currency_to_input, CURRENCY_AVAILABLE).all:
        await update.message.reply_text(
            "Неверные данные, пожалуйста, попробуйте снова.",
            reply_markup=ReplyKeyboardRemove()
        )
        result = ConversationHandler.END
    else:
        context.user_data["currency_to"] = currency_to_input
        if not context.user_data["BYN"]:
            currency_to = set(currency_to_input)
            currency_from = set(context.user_data["currency_from"])
            if currency_to & currency_from:
                await update.message.reply_text(
                    "Пожалуйста, выберите разные валюты.",
                    reply_markup=ReplyKeyboardRemove()
                )
                result = ConversationHandler.END
        if result is not ConversationHandler.END:
            await update.message.reply_text(
                "Выберите способ обмена.",
                reply_markup=ReplyKeyboardMarkup(
                    EXCHANGE_CHOICE_WAY, one_time_keyboard=True
                ),
            )
    return result


async def exchange_way_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    exchange_way = [
        way
        for way in EXCHANGE_CHOICE_WAY[0]
        if way[0] in update.message.text
    ]
    if not exchange_way:
        await update.message.reply_text(
            "Неверные данные, пожалуйста, попробуйте снова.",
            reply_markup=ReplyKeyboardRemove()
        )
    else:
        if context.user_data['BYN']:
            request = f'http://{FAST_API_HOST}:{FAST_API_PORT}' + '/currency/BYN'
            params = {
                'currency_to': context.user_data['currency_to'],
                'exchange_way': exchange_way
            }
        else:
            request = f'http://{FAST_API_HOST}:{FAST_API_PORT}' + '/currency/conversion'
            params = {
                'currency_to': context.user_data['currency_to'],
                'exchange_way': exchange_way,
                'currency_from': context.user_data['currency_from']
            }

        response = requests.get(request, params)
        await update.message.reply_text(
            response.json()
        )
    return ConversationHandler.END

async def cancel(update, context):
    await update.message.reply_text("Диалог отменен.")
    return ConversationHandler.END

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f'Update {update} caused error {context.error}')

if __name__ == '__main__':
    print('Bot Started')

    app = Application.builder().token(f'{TELEGRAM_BOT_KEY}').build()

    conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                    CHOICE: [CallbackQueryHandler(process_choice)],
                    FAQ: [MessageHandler(None, faq_response)],
                    ATM: [MessageHandler(None, closest_atm)],
                    # CURRENCY: [MessageHandler(None, currency_exchange)],
                    DEFAULT_EXCHANGE: [MessageHandler(filters.TEXT, default_exchange_command)],
                    CURRENCY_FROM: [MessageHandler(filters.TEXT, currency_from_command)],
                    CURRENCY_TO: [MessageHandler(filters.TEXT, currency_to_command)],
                    EXCHANGE_WAY: [MessageHandler(filters.TEXT, exchange_way_command)],
            }, fallbacks=[CommandHandler("cancel", cancel)]
        )

    app.add_error_handler(error)

    app.add_handler(conv_handler)
    # app.add_handler(CallbackQueryHandler(process_choice))

    print('Bot polling')
    app.run_polling(poll_interval=3)