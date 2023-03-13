# Welcome to the friendly-splash-bot repository!

## History

Over the last two years, I have come up with quite a lot of small scripts for Eve-Online over the course of theorycrafting on [friendly-splash.space](https://friendly-splash.space/). Originally, these would live in some collab notebook that people would have to run, which was always a hassle for non-coding people. At the same time I had also picked up after propeine's awesome Killbucket bot broke due to some API changes. So eventually I decided to slowly move all of these scripts over to this discord bot, and make commands, so that the days of using colab scripts are over. If you just want to use some function, you can use the bot at the [Friendly-Splash Discord](https://discord.gg/pbhqQSVmV4) or maybe also the <10 Discord.

## Running

This repository serves as a way that you can look at the individual algorithms and things that I have implemented for your own use.
If you happen to want to mess around with stuff, I still have quite a lot of the original collab scripts uppon request.

## Inviting the bot to your Discord

You can use the following [invite link](https://discord.com/api/oauth2/authorize?client_id=903314259092590643&permissions=52224&scope=bot)

Please note that some of these commands are somewhat computationally (or network) expensive. Currently my server is handling this just fine, but I might have to limit restrict where the bot runs in the future.

## Installing the bot on your own server

1. Git pull the repo
2. Install the requirements.txt
3. Head over to the [Discord Developer Page](https://discord.com/developers/applications) and create an application, then copy the Token from the Bot page
4. Create a json file with your discord token in the bots directory named 'secrets.json' and cointaining something like this
    ```json
    {
     "TOKEN": "----------YOUR DISCORD TOKEN GOES HERE------------"
    }
    ```
5. run main.py
6. Invite the bot to your discord server with 52224 as permission in the invite link. 
 It should look something like this: `https://discord.com/api/oauth2/authorize?client_id=___something____&permissions=52224&scope=bot`

## Installing the bot on your own server

If you want to remove commands, you can simply remove the files you don't need in `commands/` and restart the bot.
For adding new ones, use the same structure of function as in the current commands: 
```python
def command_something(arguments: dict, message: DiscordMessage):
   ...
```

## Commands available


- !killbucket (originally from the Killbucket Discord Bot, with some extra stuff)
- !!linkkb (originally from the Killbucket Discord Bot)
- !stonks (originally from the Killbucket Discord Bot, I just always kept it)
- !teams (originally from the Killbucket Discord Bot, I just always kept it)
- !roll (given a set of ships, tells you how to roll your wh, and deals with mass already trough or uncertainty)
- !heat (gives you the best heating layout for some amount of highslots)
- !blob-factor (the infamous one)
- !nano-factor
- !corp-stats
- !snakes, !crystals ... (gives you pareto-optimal implant sets for a price range)

All commands take --help to show their arguments, and a bot takes !help to to show you all commands on that instance of the bot.
