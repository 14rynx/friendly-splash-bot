import yfinance as yf
from discord.ext import commands


@commands.command()
async def stonks(ctx, ticker):
    """
    !stonks <stock_ticker>
    """

    try:
        ticker_df = yf.Ticker(ticker).history(period='1d')
        await ctx.send(f"{ticker} Current Price= {round(ticker_df['Close'][0], 4)}")
    except Exception as e:
        await ctx.send("An Error Ocurred while trying to read that Ticker. " + help_message)


async def setup(bot):
    bot.add_command(stonks)
