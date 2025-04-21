from discord.ext import tasks
import discord
import asyncio
import urllib.request

client = discord.Client(intents=discord.Intents.default())

web_domain = "https://siliconpr0n.org/"

@tasks.loop(seconds=10.0)
async def fetch_post_pic():
    print("loop")
    global pic_channel
    global last_url
    contents = urllib.request.urlopen(web_domain + "gallery.txt").read().decode("utf-8")
    thumb_link = contents.split("\n")[0].split("\t")[1]
    map_link = contents.split("\n")[0].split("\t")[2]
    print(thumb_link)
    print(map_link)
    if thumb_link != last_url:
        print("Send new one")
        last_url = thumb_link
        embed = discord.Embed(title = "New picture drop !", url=web_domain + map_link, description="Can add fields etc following data on the server")
        embed.set_thumbnail(url=web_domain + thumb_link)
        await pic_channel.send(embed=embed)
    else:
        print("Still old one")

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    global pic_channel
    pic_channel = client.get_channel(CHANID_HERE)
    global last_url
    last_url = ""
    fetch_post_pic.start()

client.run('TOKEN_HERE')
