import yfinance as yf

help_message = "Usage:\n!stonks <stock_ticker>"


async def command_stonks(arguments, message):
    if "help" in arguments:
        await message.channel.send(help_message)
        return

    try:
        ticker = arguments[""][0]
        ticker_df = yf.Ticker(ticker).history(period='1d')
        await message.channel.send(f"{ticker} Current Price= {round(ticker_df['Close'][0], 4)}")
    except Exception as e:
        await message.channel.send("An Error Ocurred while trying to read that Ticker. " + help_message)
