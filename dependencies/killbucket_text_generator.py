import random


def help_text(character_days, corporation_days, alliance_days):
    return '**calculates buckets based on recent amount of Pilots involved in Killmails: **\n' \
            f' - For Characters         {character_days} Days \n' \
            f' - For Corporations       {corporation_days} Days \n' \
            f' - For Alliances               {alliance_days} Days \n\n' \
            '**And then assigns them into groups:**\n' \
            ' - For Small Gang     1 -   9 pilots\n' \
            ' - For Mid Gang     10 - 29 pilots\n' \
            ' - For Blob              30 +      pilots\n\n' \
            '**Usage:**\n' \
            '!killbucket name/characterID\n\n' \
            ' -h, --help                shows this message\n' \
            ' -a, --alliance          searches for an alliance\n' \
            ' -c, --corporation   searches for a corporation\n\n' \
            '*Other Functions: \n!stonks, !teams, !linkkb, !bucketboard*'


def judgment_phrase_generator(name, id, kills, days, group):
    if not group:
        if sum(kills.values()) < days / 4:
            return f"{name} - you are a true discord warrior!"

        small_gang = kills['solo'] + kills['five'] + kills['ten']
        blob_gang = kills['forty'] + kills['fifty'] + kills['blob']
        mid_gang = kills['fifteen'] + kills['twenty'] + kills['thirty']

        if id == 2113113522:
            return "<@242164531151765505> someone is looking for you"

        if max(kills, key=lambda key: kills[key]) == 'solo':
            return character_solo_generator(name) + character_activity_generator(name, kills, days / 2)  # One Kill every other day
        elif small_gang < blob_gang and mid_gang < blob_gang:
            return character_blobber_generator(name) + character_activity_generator(name, kills, 2 * days)  # Two Kills a day
        elif mid_gang > small_gang:
            return character_midgang_generator(name) + character_activity_generator(name, kills, 2 * days)  # Two Kills a day
        else:
            return character_smallgang_generator(name) + character_activity_generator(name, kills, days)  # One Kill a day
    else:
        if sum(kills.values()) < days / 2:
            return f"{name} - you guys are true discord warriors!"

        small_gang = kills['solo'] + kills['five'] + kills['ten']
        blob_gang = kills['forty'] + kills['fifty'] + kills['blob']
        mid_gang = kills['fifteen'] + kills['twenty'] + kills['thirty']

        if kills['solo'] > max(small_gang, mid_gang, blob_gang):
            return group_solo_generator(name)
        elif small_gang < blob_gang and mid_gang < blob_gang:
            return group_blobber_generator(name)
        elif mid_gang > small_gang:
            return group_midgang_generator(name)
        else:
            return group_smallgang_generator(name)

def start_phrase_generator(group):
    if not group:
        return random.choice([
           'You are probably a filthy blobber, we\'ll see.',
           'Small gang best gang.', 'Backpacks dont\'t count.',
           'Strix Ryden #2!',
           'I miss offgrid links.',
           'You and 4 alts is BARELY solo.',
           'Damn Pyfa warriors'
        ])
    else:
        return random.choice([
            'You are probably all filthy blobbers, we\'ll see.',
            'Small gang best gang.', 'Backpacks dont\'t count.',
            'Strix Ryden #2!',
            'We miss offgrid links',
            '9 dudes with 5 alts is barely less than ten',
            'Pyfa Warrior Alliance Please Ignore'
        ])


def character_solo_generator(name):
    return f' **{name} - You don\'t have many friends do you?**'


def character_smallgang_generator(name):
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


def character_blobber_generator(name):
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


def character_midgang_generator(name):
    return random.choice([
        f'You should probably listen to <10 instead of TiS.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Well you tried, but you should try harder.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Guess you must be a response fleet whore\n**{name} - Almost...still not cool enough to be elitist**',
        f'Probably an input broadcaster.\n**{name} - Almost...still not cool enough to be elitist**',
        f'So you, your five friends each with 3 alts. Got it.\n**{name} - Almost...still not cool enough to be elitist**'
    ])


def character_activity_generator(name, kill_buckets, requirement):
    if sum(kill_buckets.values()) < requirement:
        return f"\n And you don\'t undock much, do you?"
    return ""


def group_solo_generator(name):
    return f' **{name} - Duh, do you all play for your own?**'


def group_smallgang_generator(name):
    return random.choice([
        f'Does your group do Mouse SRP?\n**{name} - You\'re all elitist nano pricks**',
        f'What\'s an anchor and why do I need one?\n**{name} - You\'re all elitist nano pricks**',
        f'We don\'t need no stinking FC.\n**{name} - You\'re all elitist nano pricks**',
        f'This is a battlefield, not a drag race!\n**{name} - You\'re all elitist nano pricks**',
        f'How many backpacks do you lose?\n**{name} - You\'re all elitist nano pricks**',
        f'Keepstar anchored - Vonhole invited\n**{name} - You\'re all elitist nano pricks**',
        f'Don\'t forget your HG snake pods\n**{name} - You\'re all elitist nano pricks**',
        f'So many 100mns, must be a Tuskers copy\n**{name} - You\'re all elitist nano pricks**'
    ])


def group_blobber_generator(name):
    return random.choice([
        f'FC when do I hit F1?\n**{name} - Don\'t forget your 5 Monitors**',
        f'FC can I bring my drake?\n**{name} - You\'re all blobbers**',
        f'Who is the anchor?\n**{name} - Blobbers, Blobbers, blobbers ... and a few more**',
        f'How\'s that blue donut treating you?\n**{name} - - You\'re all blobbers**',
        f'You must be some "feared" nullsec group.\n**{name} - You\'re all blobbers**',
        f'Theorycrafting is only for FC\'s right? \n**{name} - - You\'re all blobbers**',
        f'Sky marshall said stay docked.\n**{name} - - You\'re all blobbers**',
        f'At least you have a strong presence on reddit! \n**{name}- You\'re all blobbers**'
    ])


def group_midgang_generator(name):
    return random.choice([
        f'You should probably listen to <10 instead of TiS.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Well you guys tried, but you should try harder.\n**{name} - Almost...still not cool enough to be elitist**',
        f'Enough dudes on grid so that they surely all are tackled? \n**{name} - Not quite enough to be **',
        f'Protean Concept would be proud with so many OP ships on a Grid\n**{name} - Go from C4 to C2 and you are worth something **',
        f'Probably an input broadcaster.\n**{name} - Almost...still not cool enough to be elitist**',
        f'So you, your five friends each with 3 alts. Got it.\n**{name} - Almost...still not cool enough to be elitist**'
    ])
