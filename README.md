# Welcome to the friendly-splash-bot repository!

##History

Over the last two years, I have come up with quite a lot of small scripts for Eve-Online over the course of theorycrafting on [friendly-splash.space](https://friendly-splash.space/).

Originally, these would live in some collab notebook that people would have to run, which was always a hassle for non-coding people, so I decided to slowly move all of these scripts over to this discord bot.
If you just want to use some script, you can use the bot at the [Friendly-Splash Discord](https://discord.gg/pbhqQSVmV4).

## Running

This repository serves as a way that you can look at the individual algorithms and things that I have implemented for your own use.
If you happen to want to mess around with stuff, I still have quite a lot of the original collab scripts uppon requests.

## Installing the bot on your own server

1. Git pull the repo
2. Install the requirements.txt
3. Set zo an enviroment variable called `TOKEN` with your discord bot token
4. run main.py

If you want to add / remove commands, you can simply remove the files you don't need in `commands/` or add your own.

## Commands available


- killbucket (originally from the Killbucket Discord Bot, with some extra stuff)
- linkkb (originally from the Killbucket Discord Bot)
- stonks (originally from the Killbucket Discord Bot, I just always kept it)
- teams (originally from the Killbucket Discord Bot, I just always kept it)
- roll (given a set of ships, tells you how to roll your wh, and deals with mass already trough or uncertainty)
- scrape (scrapes zkillboard for un-linked kills)
- heat (gives you the best heating layout for some amount of highslots)
- blob-factor (the infamous one)
- nano-factor
- corp-stats