import logging

import yfinance as yf
from discord.ext import commands

# Configure the logger
logger = logging.getLogger('discord.heat')
logger.setLevel(logging.INFO)


@commands.command()
async def stonks(ctx, ticker):
    """
    !stonks <stock_ticker>
    """
    logger.info(f"{ctx.author.name} used !stonks {ticker}")
    try:
        ticker_df = yf.Ticker(ticker).history(period='1d')
        await ctx.send(f"{ticker} Current Price= {round(ticker_df['Close'][0], 4)}")
    except Exception as e:
        await ctx.send("An Error Ocurred while trying to read that Ticker.")


async def setup(bot):
    bot.add_command(stonks)
