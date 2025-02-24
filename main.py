#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "ipetrash"


import time

from telegram.ext import Application

import commands

from config import TOKEN
from common import log


async def post_init(app: Application) -> None:
    log.debug(f"Bot name {app.bot.first_name!r} ({app.bot.name})")


def main() -> None:
    log.debug("Start")

    app = (
        Application
        .builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )

    commands.setup(app)

    app.run_polling()

    log.debug("Finish")


if __name__ == "__main__":
    while True:
        try:
            main()
        except:
            log.exception("")

            timeout = 15
            log.info(f"Restarting the bot after {timeout} seconds")
            time.sleep(timeout)
