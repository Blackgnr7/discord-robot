import os 
from dotenv import load_dotenv
import discord
import discord.ext.commands

load_dotenv()
discord_token = os.getenv("discord_token")

intents = discord.Intents.all()

comand = discord.ext.commands.Bot(intents=intents)  

palavras_pobribidas = {
    1058449539197059175:{"puta", }
}

@comand.event
async def on_ready():
    print(f'Logged in as {comand.user}')
    await comand.sync_commands()

@comand.event
async def on_member_remove(menber):
    await menber.send(f"saiu do servidor {menber.user}")

@comand.event
async def on_member_join(menber):
    await menber.send(f"entro no servidor {menber.user}")

@comand.event
async def on_message(message):
    if(message.author == comand.user):
        pass
    else:
        for proibidas in palavras_pobribidas.get(message.guild.id):
            if proibidas in message.content.lower():
                print(proibidas)
                await message.delete()
                await message.channel.send(f"não é permitido usar essa palavra {message.author.mention}")
        if "bo jogar" in message.content.lower():
            await message.channel.send(f"talvez {message.author.mention}")

@comand.slash_command(name="ping", description="Mostra a latência do bot")
async def ping(ctx):
    latency_ms = round(comand.latency * 1000)
    await ctx.respond(f"Pong! A latência é de {latency_ms}ms")

@comand.slash_command(name="id_servidor", description="saber o id do servidor mais facilmente")
async def id_servidor(ctx):
    await ctx.respond(f"o servidor {ctx.guild.name} o id dele é {ctx.guild.id}")

@comand.slash_command(name="add_palavras_proibidas", description="adicionar a palavra que queira para a dicionaria de palavras proibidas")
@discord.ext.commands.has_role('lider')
async def add(ctx, args):
    for palavra in palavras_pobribidas:
        if palavra == ctx.guild.id:
            pass
        else:
            palavras_pobribidas[ctx.guild.id] = "puta"
    print(args)
    palavras_pobribidas[ctx.guild.id].add(str(args))
    print(palavras_pobribidas)
    await ctx.respond(f"o servidor {ctx.guild.name} o id dele é {ctx.guild.id}")    

@comand.slash_command(name="help", description="mostra todos os comandos possiveis de se usar")
async def help(ctx):
    embed = discord.Embed(
        title="mostrar como usar cada comando do bot",
        color=discord.Colour.purple()
    )
    embed.add_field(name="/ping", value=f"mostra o ping do bot {comand.user}")
    embed.add_field(name="/add_palavras_proibidas", value="faz que adiciona uma palavra para a dicionario de palavras proibidas")
    embed.add_field(name="/id_servidor", value="usado para mostrar o id do servidor facilmente")   
    embed.add_field(name="/ping", value=f"mostra o ping do bot {comand.user}")
    embed.add_field(name="/add_palavras_proibidas", value="faz que adiciona uma palavra para a dicionario de palavras proibidas")
    embed.add_field(name="/id_servidor", value="usado para mostrar o id do servidor facilmente")  
    await ctx.respond(embed=embed)

comand.run(discord_token)