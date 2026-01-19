import os
import json
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
from pytubefix import Search
import yt_dlp

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

YDL_OPTIONS = {"format": "bestaudio/best", "noplaylist": True}

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

if not DISCORD_TOKEN:
    print("ERRO: DISCORD_TOKEN não encontrado no arquivo .env")
    print("Por favor, adicione seu token do Discord no arquivo .env")
    exit(1)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

DATA_FILE = Path("data/palavras_proibidas.json")
DATA_FILE.parent.mkdir(exist_ok=True)


def carregar_palavras_proibidas():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {int(k): set(v) for k, v in data.items()}
    return {}


def salvar_palavras_proibidas(palavras):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        data = {str(k): list(v) for k, v in palavras.items()}
        json.dump(data, f, ensure_ascii=False, indent=2)


palavras_proibidas = carregar_palavras_proibidas()


@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")
    print(f"ID: {bot.user.id}")
    print("------")
    await bot.tree.sync()
    print("Comandos slash sincronizados!")


@bot.event
async def on_member_remove(member):
    try:
        canal_sistema = member.guild.system_channel
        if canal_sistema:
            await canal_sistema.send(
                f"👋 {member.mention} saiu do servidor {member.guild.name}"
            )
    except Exception as e:
        print(f"Erro ao enviar mensagem de saída: {e}")


@bot.event
async def on_member_join(member):
    try:
        await member.send(f"Bem-vindo(a) ao servidor {member.guild.name}! 👋")
    except discord.Forbidden:
        print(f"Não foi possível enviar DM para {member.name} (DMs desativadas)")
    except Exception as e:
        print(f"Erro ao enviar mensagem de boas-vindas: {e}")

    try:
        canal_sistema = member.guild.system_channel
        if canal_sistema:
            await canal_sistema.send(f"Bem-vindo(a) {member.mention}! 🎉")
    except Exception as e:
        print(f"Erro ao enviar mensagem no canal: {e}")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if not message.guild:
        return

    guild_id = message.guild.id
    palavras_servidor = palavras_proibidas.get(guild_id)

    mensagem_lower = message.content.lower()

    for palavra_proibida in palavras_servidor:
        if palavra_proibida in mensagem_lower:
            try:
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention}, não é permitido usar essa palavra!",
                    delete_after=5,
                )
                print(
                    f"Mensagem deletada de {message.author} contendo: {palavra_proibida}"
                )
            except discord.Forbidden:
                print(f"Sem permissão para deletar mensagem em {message.guild.name}")
            except Exception as e:
                print(f"Erro ao processar mensagem: {e}")
            return

    if "bo jogar" in mensagem_lower:
        await message.channel.send(f"Talvez... 🤔 {message.author.mention}")

    await bot.process_commands(message)


@bot.tree.command(name="ping", description="Mostra a latência do bot")
async def ping(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! A latência é de {latency_ms}ms")


@bot.tree.command(name="id_servidor", description="Mostra o ID do servidor")
async def id_servidor(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Informações do Servidor", color=discord.Colour.purple()
    )
    embed.add_field(name="Nome", value=interaction.guild.name, inline=False)
    embed.add_field(name="ID", value=f"`{interaction.guild.id}`", inline=False)
    embed.add_field(name="Membros", value=interaction.guild.member_count, inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(
    name="add_palavra_proibida",
    description="Adiciona uma palavra à lista de palavras proibidas",
)
@commands.has_role("lider")
async def add_palavra(interaction: discord.Interaction, palavra: str):
    guild_id = interaction.guild.id
    palavra_lower = palavra.lower().strip()

    if guild_id not in palavras_proibidas:
        palavras_proibidas[guild_id] = set()

    if palavra_lower in palavras_proibidas[guild_id]:
        await interaction.response.send_message(
            f"⚠️ A palavra `{palavra_lower}` já está na lista de proibidas!",
            ephemeral=True,
        )
        return

    palavras_proibidas[guild_id].add(palavra_lower)
    salvar_palavras_proibidas(palavras_proibidas)

    await interaction.response.send_message(
        f"✅ Palavra `{palavra_lower}` adicionada à lista de proibidas!", ephemeral=True
    )
    print(f"Palavra '{palavra_lower}' adicionada ao servidor {interaction.guild.name}")


@bot.tree.command(
    name="remover_palavra_proibida",
    description="Remove uma palavra da lista de palavras proibidas",
)
@commands.has_role("lider")
async def remover_palavra(interaction: discord.Interaction, palavra: str):
    guild_id = interaction.guild.id
    palavra_lower = palavra.lower().strip()

    if (
        guild_id not in palavras_proibidas
        or palavra_lower not in palavras_proibidas[guild_id]
    ):
        await interaction.response.send_message(
            f"⚠️ A palavra `{palavra_lower}` não está na lista de proibidas!",
            ephemeral=True,
        )
        return

    palavras_proibidas[guild_id].remove(palavra_lower)
    salvar_palavras_proibidas(palavras_proibidas)

    await interaction.response.send_message(
        f"✅ Palavra `{palavra_lower}` removida da lista de proibidas!", ephemeral=True
    )
    print(f"Palavra '{palavra_lower}' removida do servidor {interaction.guild.name}")


@bot.tree.command(
    name="listar_palavras_proibidas",
    description="Mostra todas as palavras proibidas neste servidor",
)
@commands.has_role("lider")
async def listar_palavras(interaction: discord.Interaction):
    guild_id = interaction.guild.id
    palavras_servidor = palavras_proibidas.get(guild_id, set())

    if not palavras_servidor:
        await interaction.response.send_message(
            "📝 Nenhuma palavra proibida configurada neste servidor.", ephemeral=True
        )
        return

    embed = discord.Embed(
        title="🚫 Palavras Proibidas",
        description=f"Total: {len(palavras_servidor)} palavras",
        color=discord.Colour.red(),
    )

    lista_palavras = ", ".join([f"`{p}`" for p in sorted(palavras_servidor)])
    embed.add_field(name="Palavras", value=lista_palavras, inline=False)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="stop", description="parar musica quando quiser")
async def play(interaction: discord.Integration):
    vc = interaction.guild.voice_client

    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message(
            f"🔊 {bot.user.mention} saiu do canal de voz", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {bot.user.mention} não está em nenhum canal de voz", ephemeral=True
        )


@bot.tree.command(name="play", description="colocar musica e a pesquisa é no youtube")
async def play(interaction: discord.Interaction, url: str):
    await interaction.response.defer()
    if not interaction.user.voice:
        await interaction.followup.send(
            "❌ entre em uma call de voz, por favor", ephemeral=True
        )
        return
    voice_channel = interaction.user.voice.channel
    if not interaction.guild.voice_client:
        await voice_channel.connect()
    voice_client = interaction.guild.voice_client
    resultado = Search(url)
    videos = resultado.videos[0]
    url_achado = videos.watch_url
    titulo = videos.title
    with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url_achado, download=False)
        audio_url = info["url"]
    source = discord.FFmpegOpusAudio(audio_url, **FFMPEG_OPTIONS)
    if voice_client.is_playing():
        voice_client.stop()
    voice_client.play(source)
    await interaction.followup.send(f"🎶 Tocando agora: **{titulo}**")


@bot.tree.command(
    name="search", description="pesquisar videos do youtube e mostrar para todo mundo"
)
async def search(interaction: discord.Interaction, url: str):
    print(url)
    resultado = Search(url)
    for videos in resultado.videos:
        await interaction.response.send_message(videos.watch_url)


@bot.tree.command(name="help", description="Mostra todos os comandos disponíveis")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 Comandos do Bot",
        description="Lista de todos os comandos disponíveis",
        color=discord.Colour.purple(),
    )

    embed.add_field(name="🏓 /ping", value="Mostra a latência do bot", inline=False)
    embed.add_field(
        name="📋 /id_servidor",
        value="Mostra informações e ID do servidor",
        inline=False,
    )
    embed.add_field(
        name="➕ /add_palavra_proibida",
        value="Adiciona uma palavra à lista de proibidas (requer role 'lider')",
        inline=False,
    )
    embed.add_field(
        name="➖ /remover_palavra_proibida",
        value="Remove uma palavra da lista de proibidas (requer role 'lider')",
        inline=False,
    )
    embed.add_field(
        name="📝 /listar_palavras_proibidas",
        value="Lista todas as palavras proibidas (requer role 'lider')",
        inline=False,
    )
    embed.add_field(
        name="❓ /help", value="Mostra esta mensagem de ajuda", inline=False
    )

    embed.set_footer(text=f"Bot: {bot.user.name}")

    await interaction.response.send_message(embed=embed, ephemeral=True)


@add_palavra.error
@remover_palavra.error
@listar_palavras.error
async def role_error(interaction: discord.Interaction, error):
    if isinstance(error, commands.MissingRole):
        await interaction.response.send_message(
            "❌ Você precisa ter a role 'lider' para usar este comando!", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ Erro ao executar comando: {str(error)}", ephemeral=True
        )
        print(f"Erro: {error}")


if __name__ == "__main__":
    print("Iniciando o bot...")
    bot.run(DISCORD_TOKEN)
