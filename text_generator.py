import random


def phrase_generator(name, kills, days):
    if sum(kills.values()) < days / 4:
        return f"{name} - you are a true discord warrior!"
    small_gang = kills['solo'] + kills['five'] + kills['ten']
    blob_gang = kills['forty'] + kills['fifty'] + kills['blob']
    mid_gang = kills['fifteen'] + kills['twenty'] + kills['thirty']
    if max(kills, key=lambda key: kills[key]) == 'solo':
        return solo(name) + activity(name, kills, days / 2)  # One Kill every other day
    elif small_gang < blob_gang and mid_gang < blob_gang:
        return blobber(name) + activity(name, kills, 2 * days)  # Two Kills a day
    elif mid_gang > small_gang and mid_gang > blob_gang:
        return midgang(name) + activity(name, kills, 2 * days)  # Two Kills a day
    else:
        return smallgang(name) + activity(name, kills, days)  # One Kill a day


def help_text(days):
    return 'Usage: Place character id or name after !killbucket \n' \
           f'Calculates buckets based on pilots involved for the last {days} days\n' \
           'Small Gang: involved pilots < 10 \n ' \
           'Mid Gang: 10 <= involved pilots < 30\n' \
           'Blob: 30 <= involved pilots'


def start_generator():
    return random.choice([
       'You are probably a filthy blobber, we\'ll see.',
       'Small gang best gang.', 'Backpacks dont\'t count.',
       'Strix Ryden #2!',
       'I miss offgrid links.',
       'You and 4 alts is BARELY solo.',
       'Damn Pyfa warriors'
    ])


def solo(name):
    return f' **{name} - You don\'t have many friends do you?**'


def smallgang(name):
    return random.choice([
        f'Did you wear your mouse out clicking in space?\n**{name} - You\'re an elitist nano prick**',
        f'What\'s an anchor and why do I need one?\n**{name} - You\'re an elitist nano prick**',
        f'We don\'t need no stinking FC.\n**{name} - You\'re an elitist nano prick**',
        f'Kitey nano bitch.\n**{name} - You\'re an elitist nano prick**',
        f'How many backpacks do you lose?\n**{name} - You\'re an elitist nano prick**',
        f'Wormholer BTW\n**{name} - You\'re an elitist nano prick**',
        f'Don\'t forget your HG snake pod\n**{name} - You\'re an elitist nano prick**',
        f'You\'d be even more elite with some purple on that ship.\n**{name} - You\'re an elitist nano prick**'
    ])


def blobber(name):
    return random.choice([
        f'FC when do I hit F1?\n**{name} - You\'re a blobber**',
        f'FC can I bring my drake?\n**{name} - You\'re a blobber**',
        f'Who is the anchor?\n**{name} - You\'re a blobber**',
        f'How\'s that blue donut treating you?\n**{name} - You\'re a blobber**',
        f'You must be part of some nullsec alliance.\n**{name} - You\'re a blobber**',
        f'You\'ve never heard of a nanofiber have you.\n**{name} - You\'re a blobber**',
        f'My sky marshall said stay docked.\n**{name} - You\'re a blobber**',
        f'I bet you\'ve got the record in your alliance for station spin counter though! \n**{name} - You\'re a blobber**'
    ])


def midgang(name):
    return random.choice([
        f'You should probably listen to <10 instead of TiS.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Well you tried, but you should try harder.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Guess you must be a response fleet whore\n**{name} - Almost...still not cool enough to be elitist**',
        f'Probably an input broadcaster.\n**{name} - Almost...still not cool enough to be elitist**',
        f'So you, your five friends each with 3 alts. Got it.\n**{name} - Almost...still not cool enough to be elitist**'
    ])


def activity(name, kills, requirement):
    if sum(kills.values()) < requirement:
        return f"\n And you don\'t undock much, do you?"
    return ""
