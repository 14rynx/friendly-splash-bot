import json
import requests
import time



leaderboard ={
    'solo':{
        'first':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'second':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'third':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        }
    },
    'five':{
        'first':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'second':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'third':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        }
    },
    'ten':{
        'first':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'second':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'third':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        }
    },
    'twenty':{
        'first':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'second':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'third':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        }
    },
    'blob':{
        'first':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'second':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        },
        'third':{
            'pilot':0,
            'pilotname':"",
            'count':0,
        }
    }
}


def char_id_lookup(char_name):
    pull_url = "https://esi.evetech.net/legacy/search/?categories=character&datasource=tranquility&language=en-us&search={}&strict=true"
    resp = requests.get(pull_url.format(char_name))
    data = resp.json()
    return data['character'][0]

def char_name_lookup(char_id):
    try:
        pull_url = "https://esi.evetech.net/latest/characters/{}/?datasource=tranquility"
        resp = requests.get(pull_url.format(char_id))
        data = resp.json()
        return data['name']
    except:
        return "__malfunction__"

def get_killbucket(char_id):
    try:
        page_num = 1
        pilots_involved = {
            "solo": 0,
            "five": 0,
            "ten": 0,
            "twenty": 0,
            "blob": 0,
        }
        try:
            int_char_id = int(char_id)
        except ValueError:
            try:
                int_char_id = float(char_id)
            except ValueError:
                int_char_id = int(char_id_lookup(char_id))

        # set up initial webpage hit
        link = f"https://zkillboard.com/api/kills/characterID/{int_char_id}/pastSeconds/604800/no-attackers/page/{page_num}/"

        # req = requests.get(link, headers={'Accept-Encoding': 'gzip', "User-Agent": "propeine-bot"})
        # res = req.json()

        response = requests.session()
        response.headers.update(
            {'Accept-Encoding': 'gzip', "User-Agent": "propeine-bot"})
        response = requests.get(link)

        # zkill returns [] if the page is empty
        while response.text.find("[]") == -1 and page_num<6:
            print("Reading page: " + str(page_num))
            cjson = json.loads(response.text)
            for i in range(len(cjson)):
                pilots = int(cjson[i]['zkb']['involved'])
                if int(pilots) == 1:
                    pilots_involved["solo"] += 1
                elif int(pilots) < 5:
                    pilots_involved["five"] += 1
                elif int(pilots) < 10:
                    pilots_involved["ten"] += 1
                elif int(pilots) < 20:
                    pilots_involved["twenty"] += 1
                elif int(pilots) >= 20:
                    pilots_involved["blob"] += 1
            page_num += 1
            time.sleep(0.5)
            link = f"https://zkillboard.com/api/kills/characterID/{int_char_id}/pastSeconds/604800/no-attackers/page/{page_num}/"
            response = requests.get(link)
        return pilots_involved
    except:
        return {'solo':'error'}

def update_board(pilot, char_id):
    name = char_name_lookup(char_id)
    for key in leaderboard:
        if pilot[key] > leaderboard[key]['first']['count']:
            
            #bump down current 2 to 3
            leaderboard[key]['third']['count'] = leaderboard[key]['second']['count']
            leaderboard[key]['third']['pilot'] = leaderboard[key]['second']['pilot']
            leaderboard[key]['third']['pilotname']= leaderboard[key]['second']['pilotname']
            
            #bump down current 1 to 2
            leaderboard[key]['second']['count'] = leaderboard[key]['first']['count']
            leaderboard[key]['second']['pilot'] = leaderboard[key]['first']['pilot']
            leaderboard[key]['second']['pilotname']= leaderboard[key]['first']['pilotname']

            #set new leader
            leaderboard[key]['first']['count'] = pilot[key]
            leaderboard[key]['first']['pilot'] = char_id
            leaderboard[key]['first']['pilotname']= name
        elif pilot[key] > leaderboard[key]['second']['count']:

            #bump down current 2 to 3
            leaderboard[key]['third']['count'] = leaderboard[key]['second']['count']
            leaderboard[key]['third']['pilot'] = leaderboard[key]['second']['pilot']
            leaderboard[key]['third']['pilotname']= leaderboard[key]['second']['pilotname']           

            leaderboard[key]['second']['count'] = pilot[key]
            leaderboard[key]['second']['pilot'] = char_id
            leaderboard[key]['second']['pilotname']= name

        elif pilot[key] > leaderboard[key]['third']['count']:
            leaderboard[key]['third']['count'] = pilot[key]
            leaderboard[key]['third']['pilot'] = char_id
            leaderboard[key]['third']['pilotname']= name
            
    dump_board()
    

def dump_board():
    with open('json-weekly.txt', 'w') as outfile:
        json.dump(leaderboard, outfile)  

  
# with open('jsontest.txt','r') as infile:
#     leaderboard = json.load(infile)

r = open("pilots.txt","r+")
line = r.readline()
while line:
    pilotkills = get_killbucket(line.rstrip())
    #group = max(pilotkills, key=lambda key: pilotkills[key])
    #count = pilotkills[group]
    if pilotkills['solo']!='error':
        update_board(pilotkills, line.rstrip())
    #print(line.rstrip())
    #print(line.rstrip() + '->' +char_name_lookup(line.rstrip()))
    line=r.readline()
dump_board()
print(leaderboard)
