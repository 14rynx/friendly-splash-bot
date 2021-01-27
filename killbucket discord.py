import requests
import json
import time
import os
import matplotlib.pyplot as plt
import discord
import random


plt.rcdefaults()
color = 'darkgray'
plt.rc('font', weight='bold')
plt.rcParams['text.color']=color
plt.rcParams['axes.labelcolor']=color
plt.rcParams['xtick.color']=color
plt.rcParams['ytick.color']=color
plt.rc('axes',edgecolor=color)
from keep_alive import keep_alive

client = discord.Client()

def killboard():
  leaderboard = json.loads('json-weekly.txt')

  string = ''
  for bucket in leaderboard.keys():
    string += f'**{bucket.capitalize()}:**\n'
    for place, data in leaderboard[bucket].items():
        string += f':{place}_place: {data["pilotname"]} - {data["count"]}\n'
    string += '\n'

def char_id_lookup(char_name):
    pull_url = "https://esi.evetech.net/legacy/search/?categories=character&datasource=tranquility&language=en-us&search={}&strict=true"
    resp = requests.get(pull_url.format(char_name))
    data = resp.json()
    return data['character'][0]

def get_buckets(zkill_id):
    # dictionary for how many pilots involved in killmails
    page_num = 1
    pilots_involved = {
        "solo": 0,
        "five": 0,
        "ten": 0,
        "fifteen": 0,
        "twenty": 0,
        "thirty": 0,
        "forty": 0,
        "fifty": 0,
        "blob": 0,
    }
    char_id = zkill_id 
    #input("Enter your character id from zkill: ")
    # set up initial webpage hit
    try:
        link = "https://zkillboard.com/api/kills/characterID/" + str(char_id) + "/no-attackers/page/" + \
            str(page_num) + "/"
        response = requests.session()
        response.headers.update(
            {'Accept-Encoding': 'gzip', "User-Agent": "propeine bucket bot"})
        response = requests.get(link)

        # zkill returns [] if the page is empty
        while response.text.find("[]") == -1 and page_num < 6:
            #print("Reading page: " + str(page_num))
            cjson = json.loads(response.text)
            for i in range(len(cjson)):
                pilots = int(cjson[i]['zkb']['involved'])
                if int(pilots) == 1:
                    pilots_involved["solo"] += 1
                elif int(pilots) < 5:
                    pilots_involved["five"] += 1
                elif int(pilots) < 10:
                    pilots_involved["ten"] += 1
                elif int(pilots) < 15:
                    pilots_involved["fifteen"] += 1
                elif int(pilots) < 20:
                    pilots_involved["twenty"] += 1
                elif int(pilots) < 30:
                    pilots_involved["thirty"] += 1
                elif int(pilots) < 40:
                    pilots_involved["forty"] += 1
                elif int(pilots) < 50:
                    pilots_involved["fifty"] += 1
                elif int(pilots) >= 50:
                    pilots_involved["blob"] += 1
            page_num += 1
            time.sleep(1.25)
            link = "https://zkillboard.com/api/kills/characterID/" + str(char_id) + "/no-attackers/page/" + \
                str(page_num) + "/"
            response = requests.get(link)
        return pilots_involved
    except:
        return 'error'    #if literally anything goes wrong

#setup initial login
phrases = ['You are probably a filthy blobber, we\'ll see.','Small gang best gang.','Backpacks dont\'t count.','Strix Ryden #2!','I miss offgrid links.','You and 4 alts is BARELY solo.','Damn Pyfa warriors']
smallgang_phrases=['Did you wear your mouse out clicking in space?','What\'s an anchor and why do I need one?','We don\'t need no stinking FC.','Kitey nano bitch.','How many backpacks do you lose?','Wormholer BTW','Don\'t forget your HG snake pod','You\'d be even more elite with some purple on that ship.']
blobber_phrases=['FC when do I hit F1?','FC can I bring my drake?','Who is the anchor?','How\'s that blue donut treating you?','You must be part of some nullsec alliance.','You\'ve never heard of a nanofiber have you.','My sky marshall said stay docked.','I bet youve got the record in your alliance for station spin counter though!']
midgang_phrases=['You should probably listen to <10 instead of TiS.', 'Well you tried, but you should try harder.', 'Guess you must be a response fleet whore','Probably an input broadcaster.','So you, your five friends each with 3 alts. Got it.']
@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

#if !killbucket used then get the zkill id
@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.content =='!bucketboard':
      await message.channel.send(killboard())
    if message.content.startswith('!killbucket'):
      if message.content == '!killbucket help':
        await message.channel.send('Usage:Place zkillID (from URL on zkill.com) after !killbucket \n Calculates kills based on pilots involved for buckets for the most recent 1000  kills\nSmall Gang - <10, Mid gang- 10>= kills<30, Blobber - >=30')
        print('someone asked for help')
      else:
        print('someone asked for kills for ' + message.content[12:])
        await message.channel.send(random.choice(phrases)+'\n This might take a minute...')
        kill_id = message.content[12:]
        dumb = False
        try:
          int_char_id = int(kill_id)
        except ValueError:
          try:
            int_char_id = float(kill_id)

          except ValueError:
            try:
              int_char_id = int(char_id_lookup(kill_id))
            except:
              dumb = True 

        if dumb == False:
          kills = get_buckets(int_char_id) #assumes !killbucket_zkillid
          if kills == 'error':
              await message.channel.send('Something went wrong, probably invalid zkill ID')
              print('someone screwed up')
          else:
              #message_text = ''
              small_gang = kills['solo']+kills['five']+kills['ten']
              blob_gang = kills['forty']+kills['fifty']+kills['blob']
              mid_gang = kills['fifteen']+kills['twenty']+kills['thirty']
              if max(kills, key=lambda key: kills[key]) =='solo':
                reaction_text = ' **' + kill_id +'- You don\'t have many friends do you?**'
              elif small_gang < blob_gang and mid_gang<blob_gang:
                reaction_text = random.choice(blobber_phrases) + '\n **' + kill_id +'- You\'re a blobber**'
              elif mid_gang>small_gang and mid_gang > blob_gang:
                reaction_text = random.choice(midgang_phrases) + '\n **' + kill_id +'- Almost...still not cool enough to be elitist**'
              else:
                reaction_text = random.choice(smallgang_phrases) + '\n **' + kill_id +'- You\'re an elitist nano prick**'
              if sum(kills.values()) < 1000:
                reaction_text = kill_id + ' you don\'t undock much do you'

              #build the graph              
              with open('pilots.txt',"a") as f:
                print(str(int_char_id) + "\n",file=f)
              pilots = kills.keys()
              number = kills.values()
              plt.bar(pilots, number, align='center', alpha=0.5,color=color)
              plt.ylabel('Number of Kills')
              plt.title('Involved Pilots per KM for zkillID:'+kill_id,color=color)
              fig1=plt.gcf()
              fig1.savefig(fname='plot.png',transparent=True)
              plt.clf()
              await message.channel.send(file=discord.File('plot.png'), content = reaction_text)

        else:
          await message.channel.send('I don\'t know who you\'re talking about')
              
            
keep_alive()
client.run(os.getenv('TOKEN'))          