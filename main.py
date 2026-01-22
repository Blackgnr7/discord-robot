import os
import json
from pathlib import Path
from dotenv import load_dotenv
import discord
from discord.ext import commands
from pytubefix import Search
from pytubefix import YouTube
from collections import deque

fila_de_musica = {}
loop_de_musica = {}
loop_da_fila = {}
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

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


def tocar_mucic(guild_id):
    fila = fila_de_musica.get(guild_id)
    vc = bot.get_guild(guild_id).voice_client
    if not vc and fila or len(fila) == 0:
        return
    if loop_de_musica.get(guild_id):
        music = fila[0]
    else:
        music = fila.popleft()
    source = discord.FFmpegPCMAudio(music["audio"], **FFMPEG_OPTIONS)
    vc.play(source, after=lambda e: tocar_mucic(guild_id))
    if loop_da_fila.get(guild_id) and not loop_de_musica.get(guild_id):
        fila.append(music)


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
    await interaction.response.send_message(f"A latência é de {latency_ms}ms")


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

@bot.tree.command(name="return", description="mando o bot entrar para a call")
async def voltar(interaction: discord.Integration):
    voice_client = interaction.guild.voice_client
    voice_channel = interaction.user.voice.channel
    if not voice_client:
        await voice_channel.connect()
        await interaction.response.send_message(
            f"🔙 {bot.user.mention} connectado na call", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {bot.user.mention} não está em nenhum canal de voz", ephemeral=True
        )

@bot.tree.command(name="leave", description="mando o bot para fora da call")
async def leave(interaction: discord.Integration):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message(
            f"🔚 {bot.user.mention} desconectado da call", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {bot.user.mention} não está em nenhum canal de voz", ephemeral=True
        )

@bot.tree.command(name="skip", description="skipar uma musica")
async def skipar(interaction: discord.Integration):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_playing():
        voice_client.stop()
        await interaction.response.send_message(
            f"⏩ {bot.user.mention} foi skipado a musica", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {bot.user.mention} não está em nenhum canal de voz", ephemeral=True
        )

@bot.tree.command(name="despausar", description="despausar musica")
async def despaussar(interaction: discord.Integration):
    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        await interaction.response.send_message(
            f"⏸ {bot.user.mention} foi despausado", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {bot.user.mention} não está em nenhum canal de voz", ephemeral=True
        )

@bot.tree.command(name="pausar", description="parar musica quando quiser")
async def pausar(interaction: discord.Integration):
    voice_client = interaction.guild.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        await interaction.response.send_message(
            f"▶ {bot.user.mention} foi pausado", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ {bot.user.mention} não esta ", ephemeral=True
        )


@bot.tree.command(name="play", description="colocar musica e a pesquisa é no youtube")
async def play(interaction: discord.Interaction, name: str):
    audio_url = None
    await interaction.response.defer()
    if not interaction.user.voice:
        await interaction.followup.send(
            "❌ entre em uma call de voz, por favor", ephemeral=True
        )
        return
    guuild_id = interaction.guild_id
    if guuild_id not in fila_de_musica:
        fila_de_musica[guuild_id] = deque()
    voice_channel = interaction.user.voice.channel
    if not interaction.guild.voice_client:
        await voice_channel.connect()
    voice_client = interaction.guild.voice_client
    resultado = Search(name)
    for video in resultado.videos:
        try:
            yt = YouTube(video.watch_url)
            audio_url = yt.streams.filter(only_audio=True).first()
            titulo = video.title
            break
        except Exception as e:
            print(f"Falha ao extrair áudio: {e}")

    if not audio_url:
        await interaction.followup.send(
            "❌ Não foi possível obter áudio dessa música.",
            ephemeral=True
        )
        return
    music = {"title": titulo, "audio": audio_url.url}
    fila_de_musica[guuild_id].append(music)
    if not voice_client.is_playing():
        tocar_mucic(guuild_id)
        await interaction.followup.send(f"🎶 Tocando agora: **{titulo}**")
    else:
        await interaction.followup.send(
            f"➕ adicionado na fila de musica: **{titulo}**"
        )

@bot.tree.command(name="fila", description="mostar toda o fila no momento atual")
async def search(interaction: discord.Interaction):
    fila = fila_de_musica.get(interaction.guild_id)
    vc = bot.get_guild(interaction.guild_id).voice_client
    if not vc:
        await interaction.response.send_message("❗ não tem musica ainda", ephemeral=True)
        return
    embed = discord.Embed(
        title="🎶 fila das musicas",
        description="Lista de todas as musicas atuais e sua ordem",
        color=discord.Colour.purple(),
    )
    i = 0
    for musicparaolhar in fila:
        embed.add_field(
            name=f"{i + 1}:",
            value=f"{musicparaolhar['title']}",
            inline=False,
        )
        i += 1
    embed.set_footer(text=f"Bot: {bot.user.name}")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(
    name="search", description="pesquisar videos do youtube e mostrar para todo mundo"
)
async def search(interaction: discord.Interaction, name: str):
    resultado = Search(name)
    for videos in resultado.videos:
        await interaction.response.send_message(videos.watch_url)


@bot.tree.command(
    name="loop-da-fila",
    description="ativar ou destivar o loop da fila para que a fila fique em loop para sempre",
)
async def loop(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in loop_da_fila:
        loop_da_fila[guild_id] = True
    else:
        loop_da_fila[guild_id] = not loop_da_fila[guild_id]

    status = loop_da_fila[guild_id]
    if status:
        await interaction.response.send_message("✅ ativado o loop de fila")
    else:
        await interaction.response.send_message("❌ desativado o loop de fila")


@bot.tree.command(
    name="loop-de-musica",
    description="ativar ou desativar o loop da musica para que a musica fique em loop para sempre",
)
async def loop_mucis(interaction: discord.Interaction):
    guild_id = interaction.guild_id
    if guild_id not in loop_de_musica:
        loop_de_musica[guild_id] = True
    else:
        loop_de_musica[guild_id] = not loop_de_musica[guild_id]

    status = loop_de_musica[guild_id]
    if status:
        await interaction.response.send_message("✅ ativado o loop de musica")
    else:
        await interaction.response.send_message("❌ desativado o loop de muica")


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
        name="🎶/play",
        value="ouvir musica e se ja tiver tocando adiciona em uma fila de musicas",
        inline=False,
    )
    embed.add_field(
        name="🔄 /loop-de-musica",
        value="ele disativa e ativa loop de uma so musica",
        inline=False,
    )
    embed.add_field(
        name="🔂 /loop-da-fila",
        value="ele disativa e ativa loop o loop da fila",
        inline=False,
    )
    embed.add_field(
        name="⏩ /skip",
        value="pode skipar uma musica",
        inline=False,
    )
    embed.add_field(
        name="📝 /fila",
        value="mostra o status da fila no momento",
        inline=False,
    )
    embed.add_field(
        name="▶ /pause",
        value="pode parar a musica",
        inline=False,
    )
    embed.add_field(
        name="⏸ /despausar",
        value="pode parar a musica",
        inline=False,
    )
    embed.add_field(
        name="🔚 /leave",
        value="mandar ele se desconectar da call",
        inline=False,
    )
    embed.add_field(
        name="🔙 /return",
        value="mandar ele se conectar na call",
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
