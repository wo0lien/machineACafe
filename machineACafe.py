#! \usr\bin\python3
import os
import re
import random

import discord
from dotenv import load_dotenv
from time import sleep
import sqlite3

RACE_LENGTH = 150

# connecting to the sqlite3 database to store players score
conn = sqlite3.connect("users.db")
c = conn.cursor()
# init db
c.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER, name TEXT, balance INTEGER, nbBets INTEGER DEFAULT 0, nbCafe INTEGER DEFAULT 0, PRIMARY KEY(id));')

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')

client = discord.Client()
state = 0
messages = {}
courreurs = []
parieurs = []

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    
    ########################## PARTIE CAFE ###################################

    if (re.match("(.)*(cafe|café|kfé|kfe|kaf|caf|kawa)(.)*", message.content) and not message.author.bot):
        # génération aléatoire du message

        c.execute(f'SELECT u.* FROM users u WHERE u.id={message.author.id}')
        addict = c.fetchone()
        if (addict and int(addict[2]) >= 50):
            c.execute(f'UPDATE users SET balance = balance - 45, nbCafe = nbCafe + 1 WHERE id LIKE {message.author.id};')
            rand = random.randint(1, 10)
            if rand == 1:
                await message.channel.send("Plus de gobelets déso pas déso, -45 tc-dollars") # deja -45 tc-dollars
            elif rand == 2:
                await message.channel.send("Tiens, Je rend pas la monaie par contre... -50 tc-dollars")
                c.execute(f'UPDATE users SET balance = balance - 5 WHERE id LIKE {message.author.id};') # et hop -5 tc-dollars en plus
            else:
                await message.channel.send("Bzz voila ton café :) -45 tc-dollars")
        elif(addict):
            await message.channel.send("Tu n'as pas assez d'argent... il te faut 50 tc-dollars pour prendre un café")
        else:
            await message.channel.send("Tu n'as pas parié, il te faut 50 tc-dollars pour prendre un café")
        
        conn.commit()
    
    ########################## PARTIE COURSES ###################################
    
    global state, messages, courreurs, parieurs
    
    if (message.content == "$course" and not message.author.bot and state == 0):
        state+= 1
        messages["concurrents"] = await message.channel.send("Choisissez les émojis qui vont faire la course, ensuite envoyez $ready")
        messages["course"] = message

    elif (message.content == "$ready" and not message.author.bot and state == 1):
        if (messages["concurrents"].reactions):
            state += 1
            messages["paris"] = await message.channel.send("Faites vos paris ! ensuite envoyez $start")
            
            for reaction in messages["concurrents"].reactions:
                
                #montre les possibilités de vote
                await messages["paris"].add_reaction(reaction)
                
                # création de la course
                courreurs.append({ 'reaction': reaction, 'avance': 1, 'votes': [], 'course': None})

            messages["ready"] = message
        else:
            await message.channel.send("Il faut au moins un competiteur")

    elif (message.content == "$start" and not message.author.bot and state == 2):
        state += 1
        # message recap des paris
        for courreur in courreurs:
            usersList = ""
            if not courreur["votes"]:
                usersList = "Personne n'"
            for user in courreur["votes"]:
                usersList += user.name + ", "
            await message.channel.send("{} a.ont parié.e.s pour {}".format(usersList, courreur["reaction"].emoji))
        # affichage de la course
        await message.channel.send("---------------------- Debut de la course ----------------------")
        for courreur in courreurs:            
            courreur["course"] = await message.channel.send(':triangular_flag_on_post:' + courreur["avance"] * " " + courreur["reaction"].emoji + (RACE_LENGTH - courreur["avance"]) * " " + ":checkered_flag:")
            
        # on fait la course !!!
        while True:
            # on avance un courreur random
            courreur = courreurs[random.randint(0, len(courreurs) - 1)]
            currentCourse = courreur["course"]
            courreur["avance"] += random.randint(1, 10)
            if (courreur["avance"] >= RACE_LENGTH):
                await message.channel.send("---------------------- Fin de la course ----------------------")
                strCourseFin = ":triangular_flag_on_post:" + RACE_LENGTH * " " + ":checkered_flag:" + courreur["reaction"].emoji
                await currentCourse.edit(content=strCourseFin)
                break
            strCourse = ":triangular_flag_on_post:" + courreur["avance"] * " " + courreur["reaction"].emoji + (RACE_LENGTH - courreur["avance"]) * " " + ":checkered_flag:"
            await currentCourse.edit(content=strCourse)
            sleep(random.random() * 0.3 + 0.1)

        podium = sorted(courreurs, key=lambda i: i["avance"], reverse=True)

        # update en meme temps dans la base de donnée 
        try:
            await message.channel.send(":first_place: " + podium[0]["reaction"].emoji)
            for parieur in podium[0]["votes"]:
                c.execute(f'INSERT OR IGNORE INTO users VALUES ({parieur.id}, "{parieur.name}", 0, 0, 0);')
                c.execute(f'UPDATE users SET balance = balance +  50, nbBets = nbBets + 1 WHERE id LIKE {parieur.id};')
                await message.channel.send(f'{parieur.name} a gagné 50 tc-dollars')

            await message.channel.send(":second_place: " + podium[1]["reaction"].emoji)
            for parieur in podium[1]["votes"]:
                c.execute(f'INSERT OR IGNORE INTO users VALUES ({parieur.id}, "{parieur.name}", 0, 0, 0);')
                c.execute(f'UPDATE users SET balance = balance +  40, nbBets = nbBets + 1 WHERE id LIKE {parieur.id};')
                await message.channel.send(f'{parieur.name} a gagné 40 tc-dollars')

            await message.channel.send(":third_place: " + podium[2]["reaction"].emoji)
            for parieur in podium[2]["votes"]:
                c.execute(f'INSERT OR IGNORE INTO users VALUES ({parieur.id}, "{parieur.name}", 0, 0, 0);')
                c.execute(f'UPDATE users SET balance = balance +  30, nbBets = nbBets + 1 WHERE id LIKE {parieur.id};')
                await message.channel.send(f'{parieur.name} a gagné 30 tc-dollar')
        
        finally:
            conn.commit() # udpate the changes in db
            state = 0 # back to normal state
            # clear  variables
            messages = {}
            courreurs = []
            parieurs = []


    elif(message.content == "$richiestboard" and state == 0 and not message.author.bot):
        await message.channel.send(":first_place: ---- Richiestboard ---- :first_place:")
        for index, row in enumerate(c.execute('SELECT * FROM users ORDER BY balance DESC LIMIT 10')):
            await message.channel.send(f'{index + 1} --- {row[1]} avec {row[2]} tc-dollars')

    elif(message.content == "$myscore" and state == 0 and not message.author.bot):
        c.execute(f'SELECT * FROM users WHERE id={message.author.id}')
        dbOut = c.fetchone()
        await message.channel.send(f'Il te reste {dbOut[2]} tc-dollars. Tu as fait {dbOut[3]} paris et tu as bu {dbOut[4]} cafés.')

    elif(message.content == "$help" and state == 0 and not message.author.bot):
        await message.channel.send("Liste des commandes : $course, $richiestboard, $myscore")

@client.event
async def on_reaction_add(reaction, user):
    
    # * Working
    # stockage des reactions aux messages du bot
    if (reaction.message.id == messages["concurrents"].id and reaction not in messages["concurrents"].reactions):
        messages["concurrents"].reactions.append(reaction)
    
    # stockage des paris
    if (state == 2 and reaction.message.id == messages["paris"].id and not user == client.user and user not in parieurs):
        for courreur in courreurs: # on evite les emojis qui ne sont pas en compet
            if (courreur["reaction"].emoji == reaction.emoji):
                courreur["votes"].append(user)
                parieurs.append(user) # evite les doubles votes

client.run(TOKEN)
