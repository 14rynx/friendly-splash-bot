import shelve

from urllib.parse import urlparse, parse_qs


def sanitize(inputs):
    out = []

    if len(inputs) != 3:
        raise ValueError("The input has incorrect length")

    for inp in inputs:
        int_inp = int(inp)
        if 0 < int_inp <= 5:
            out.append(int_inp)
        else:
            raise ValueError("Some Input was out of the expected range")

    return out


def average(ballots, number):
    return sum([x[number] for x in ballots.values()]) / len(ballots)


# Stolen from Stackoverflow: https://stackoverflow.com/a/7936523
def video_id(value: str) -> str:
    query = urlparse(value)
    if query.hostname == 'youtu.be':
        return query.path[1:]
    if query.hostname in ('www.youtube.com', 'youtube.com'):
        if query.path == '/watch':
            p = parse_qs(query.query)
            return p['v'][0]
        if query.path[:7] == '/embed/':
            return query.path.split('/')[2]
        if query.path[:3] == '/v/':
            return query.path.split('/')[2]
    raise ValueError


async def command_vote(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage: !vote <link to youtube video> <score1> <score2> <score3>")
        return

    vote_id = video_id(arguments[""][0])
    user_id = message.author.id

    try:
        vote_data = sanitize(arguments[""][1:])
    except (IndexError, ValueError):
        await message.channel.send("I couldn't parse your values. Make sure all scores are in [1, 5].")
        return

    with shelve.open("votes") as votes:
        if vote_id in votes:
            if user_id in votes[vote_id]:
                await message.channel.send("You already voted for this video, I am overwriting with your new scores.")
                votes[vote_id][user_id] = vote_data
            else:
                dict1 = dict(votes[vote_id])
                dict1.update({user_id: vote_data})
                votes[vote_id] = dict1
                await message.channel.send("Vote Successful!")

        else:
            await message.channel.send("I couldn't parse that video link, or there is no vote for this video.")


async def command_makevote(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage: !makevote <link to youtube video>")
        return

    vote_id = video_id(arguments[""][0])
    user_id = message.author.id

    if user_id in [183094368037502976, 242164531151765505]:  # Astrocytoma and Larynx
        with shelve.open("votes") as votes:
            if vote_id in votes:
                await message.channel.send("A vote for this video already exists, aborting!")
            else:
                votes[vote_id] = dict()
                await message.channel.send("Created an empty vote for this video.")
    else:
        await message.channel.send("You are not authorized to make new votes!")


async def command_showvote(arguments, message):
    if "help" in arguments:
        await message.channel.send("Usage: !showvote <link to youtube video>")
        return

    vote_id = video_id(arguments[""][0])

    with shelve.open("votes") as votes:
        if vote_id in votes:
            await message.channel.send(f"**Current Standings:**\n"
                                       f"Criterium 1: {average(votes[vote_id], 0)}\n"
                                       f"Criterium 2: {average(votes[vote_id], 1)}\n"
                                       f"Criterium 3: {average(votes[vote_id], 2)}\n"
                                       f"(for a total of {len(votes[vote_id])} votes)."
                                       )
        else:
            await message.channel.send("For this video currently no vote exists.")
