#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import enum
import re

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.error import BadRequest

from common import log_func, log
from config import ERROR_TEXT

from third_party.regexp import fill_string_pattern


class CounterMode(enum.Enum):
    INCREMENT = "+"
    DECREMENT = "-"
    RESET = "@"


PATTERN_COUNTER = re.compile(
    rf"^([{"".join(re.escape(x.value) for x in CounterMode)}])counter=(\d+)$"
)
PATTERN_SET_VALUE = re.compile(r"(.+)=(\d+)")


def get_button(mode: CounterMode, value: int) -> InlineKeyboardButton:
    match mode:
        case CounterMode.INCREMENT:
            text = f"➕ ({value})"
        case CounterMode.DECREMENT:
            text = "➖"
        case CounterMode.RESET:
            text = "🔄"
        case _:
            raise Exception(f"Unsupported mode: {mode}")

    return InlineKeyboardButton(
        text=text,
        callback_data=fill_string_pattern(PATTERN_COUNTER, mode.value, value),
    )


def get_inline_keyboard_markup(value: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup.from_row(
        [
            get_button(CounterMode.INCREMENT, value),
            get_button(CounterMode.DECREMENT, value),
            get_button(CounterMode.RESET, value),
        ]
    )


@log_func
async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    await update.effective_message.reply_html(
        f"Hi {user.mention_html()}!\nUse /help",
    )


@log_func
async def on_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = """
Enter any text to create a counter.
If you enter text with a "=" number, a counter with the specified value will be created. For example: "Apple=99".    
    """.strip()

    await update.effective_message.reply_text(text)


@log_func
async def on_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""

    message = update.effective_message
    text = message.text

    await message.delete()

    value = 0
    if m := PATTERN_SET_VALUE.match(text):
        text = m.group(1)
        value = int(m.group(2))

    await message.reply_text(
        text,
        reply_markup=get_inline_keyboard_markup(value),
    )


@log_func
async def on_process_counter(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    new_value: int = 0

    mode = CounterMode(context.match.group(1))

    try:
        value = int(context.match.group(2))
    except:
        value = new_value

    match mode:
        case CounterMode.INCREMENT:
            value += 1
        case CounterMode.DECREMENT:
            value -= 1
        case CounterMode.RESET:
            value = new_value
        case _:
            raise Exception(f"Unsupported mode: {mode}")

    await update.callback_query.answer()

    try:
        await update.effective_message.edit_reply_markup(
            get_inline_keyboard_markup(value)
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            return

        raise e


async def on_error_handler(
    update: Update | object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    log.error("Error: %s\nUpdate: %s", context.error, update, exc_info=context.error)

    if update:
        await update.effective_message.reply_text(text=f"⚠ {ERROR_TEXT}")


def setup(app: Application):
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("help", on_help))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_request))
    app.add_handler(
        CallbackQueryHandler(
            on_process_counter,
            pattern=PATTERN_COUNTER,
        )
    )

    app.add_error_handler(on_error_handler)
