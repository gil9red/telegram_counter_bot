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


class SettingsMode(enum.Enum):
    SHOW = "1"
    HIDE = "0"
    READ_ONLY_TRUE = "R"
    READ_ONLY_FALSE = "E"


@enum.unique
class CounterMode(enum.Enum):
    INCREMENT = "+"
    DECREMENT = "-"
    RESET = "@"
    SHOW = "1"
    HIDE = "0"
    READ_ONLY_TRUE = "R"
    READ_ONLY_FALSE = "E"


PATTERN_COUNTER = re.compile(
    rf"^([{''.join(re.escape(x.value) for x in CounterMode)}])"
    rf"counter=(\d+),"
    rf"settings=([{''.join(re.escape(x.value) for x in SettingsMode)}]+)$"
)
PATTERN_SET_VALUE = re.compile(r"(.+)=(\d+)")


def get_button(
    mode: CounterMode,
    value: int,
    settings: set[SettingsMode],
) -> InlineKeyboardButton:
    is_read_only = SettingsMode.READ_ONLY_TRUE in settings

    match mode:
        case CounterMode.INCREMENT:
            text = f"{value}" if is_read_only else f"🔼 ({value})"
        case CounterMode.DECREMENT:
            text = "🔽"
        case CounterMode.RESET:
            text = "🔄"
        case CounterMode.SHOW:
            text = "⚙️⬇"
        case CounterMode.HIDE:
            text = "⚙️⬆"
        case CounterMode.READ_ONLY_TRUE:
            text = "✅ Read only"
        case CounterMode.READ_ONLY_FALSE:
            text = "⬜ Read only"
        case _:
            raise Exception(f"Unsupported mode: {mode}")

    return InlineKeyboardButton(
        text=text,
        callback_data=fill_string_pattern(
            PATTERN_COUNTER,
            mode.value,
            value,
            "".join(x.value for x in settings)
        ),
    )


def get_inline_keyboard_markup(
    settings: set[SettingsMode],
    value: int,
) -> InlineKeyboardMarkup:
    is_hide = SettingsMode.HIDE in settings
    is_read_only = SettingsMode.READ_ONLY_TRUE in settings

    rows = [
        [
            get_button(CounterMode.INCREMENT, value, settings),
            get_button(
                CounterMode.SHOW if is_hide else CounterMode.HIDE, value, settings
            ),
        ]
    ]
    if not is_hide:
        if not is_read_only:
            rows.append(
                [
                    get_button(CounterMode.DECREMENT, value, settings),
                    get_button(CounterMode.RESET, value, settings),
                ]
            )

        rows.append(
            [
                get_button(
                    CounterMode.READ_ONLY_TRUE
                    if is_read_only
                    else CounterMode.READ_ONLY_FALSE,
                    value,
                    settings,
                ),
            ]
        )

    return InlineKeyboardMarkup(rows)


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
        reply_markup=get_inline_keyboard_markup(
            settings={SettingsMode.HIDE},
            value=value,
        ),
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

    settings = {SettingsMode(x) for x in context.match.group(3)}

    is_read_only = SettingsMode.READ_ONLY_TRUE in settings

    answer_text = None
    answer_text_read_only = "Cannot edit while read-only mode is enabled"

    match mode:
        case CounterMode.INCREMENT:
            if not is_read_only:
                value += 1
            else:
                answer_text = answer_text_read_only

        case CounterMode.DECREMENT:
            if not is_read_only:
                value -= 1
            else:
                answer_text = answer_text_read_only  # NOTE: До сюда не должно дойти, т.к. кнопка должна быть скрыта

        case CounterMode.RESET:
            if not is_read_only:
                value = new_value
            else:
                answer_text = answer_text_read_only  # NOTE: До сюда не должно дойти, т.к. кнопка должна быть скрыта

        case CounterMode.SHOW:
            settings.add(SettingsMode.SHOW)
            settings.remove(SettingsMode.HIDE)

        case CounterMode.HIDE:
            settings.add(SettingsMode.HIDE)
            settings.remove(SettingsMode.SHOW)

        case CounterMode.READ_ONLY_TRUE:
            settings.add(SettingsMode.READ_ONLY_TRUE)
            settings.remove(SettingsMode.READ_ONLY_FALSE)

        case CounterMode.READ_ONLY_FALSE:
            settings.add(SettingsMode.READ_ONLY_FALSE)
            settings.remove(SettingsMode.READ_ONLY_TRUE)

    await update.callback_query.answer(text=answer_text)

    try:
        await update.effective_message.edit_reply_markup(
            get_inline_keyboard_markup(
                settings=settings,
                value=value,
            )
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
