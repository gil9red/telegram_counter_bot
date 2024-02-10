#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import functools
import logging
import sys

from logging.handlers import RotatingFileHandler
from pathlib import Path

from telegram import Update
from telegram.ext import ContextTypes

from config import DIR_LOGS


def get_logger(
    name: str,
    file: str | Path = "log.txt",
    encoding: str = "utf-8",
    log_stdout: bool = True,
    log_file: bool = True,
) -> logging.Logger:
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    log.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] %(filename)s:%(lineno)d %(levelname)-8s %(message)s"
    )

    if log_file:
        fh = RotatingFileHandler(
            file, maxBytes=10_000_000, backupCount=5, encoding=encoding
        )
        fh.setFormatter(formatter)
        log.addHandler(fh)

    if log_stdout:
        sh = logging.StreamHandler(stream=sys.stdout)
        sh.setFormatter(formatter)
        log.addHandler(sh)

    return log


log = get_logger(__file__, DIR_LOGS / "log.txt")


def log_func(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update:
            chat_id = user_id = first_name = last_name = username = language_code = None

            if update.effective_chat:
                chat_id = update.effective_chat.id

            if update.effective_user:
                user_id = update.effective_user.id
                first_name = update.effective_user.first_name
                last_name = update.effective_user.last_name
                username = update.effective_user.username
                language_code = update.effective_user.language_code

            try:
                message = update.effective_message.text
            except:
                message = ""

            try:
                query_data = update.callback_query.data
            except:
                query_data = ""

            msg = (
                f"[chat_id={chat_id}, user_id={user_id}, "
                f"first_name={first_name!r}, last_name={last_name!r}, "
                f"username={username!r}, language_code={language_code}, "
                f"message={message!r}, query_data={query_data!r}]"
            )
            msg = func.__name__ + msg

            log.debug(msg)

        return await func(update, context)

    return wrapper
