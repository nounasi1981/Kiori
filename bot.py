import discord
import requests
import json
import os

# === 設定 ===
DISCORD_TOKEN = 'YOUR_DISCORD_BOT_TOKEN'
ADMIN_USER_IDS = [123456789012345678]  # 管理者のDiscordユーザーID
LM_API_URL = "http://localhost:1234/v1/chat"
HISTORY_DIR = "chat_histories"
MAX_HISTORY = 20

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# === 履歴ディレクトリを用意 ===
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

# === 履歴ファイルロード/保存 ===
def get_history_path(user_id):
    return os.path.join(HISTORY_DIR, f"{user_id}.json")

def load_history(user_id):
    path = get_history_path(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_history(user_id, history):
    path = get_history_path(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history[-MAX_HISTORY:], f, ensure_ascii=False, indent=2)

def reset_history(user_id):
    path = get_history_path(user_id)
    if os.path.exists(path):
        os.remove(path)

# === LM Studio へのリクエスト ===
def ask_llm(messages):
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer lm-studio"  # 通常は無視される
    }
    data = {
        "model": "local-model",  # 任意
        "messages": messages
    }
    response = requests.post(LM_API_URL, headers=headers, data=json.dumps(data))
    result = response.json()
    return result["choices"][0]["message"]["content"]

# === Discord イベント ===
@client.event
async def on_ready():
    print(f"✅ Bot connected as {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    content = message.content.strip()

    # === 管理者コマンド ===
    if content.startswith("!reset_convo"):
        if message.author.id in ADMIN_USER_IDS:
            reset_history(user_id)
            await message.channel.send("✅ 会話履歴をリセットしました。")
        else:
            await message.channel.send("❌ このコマンドは管理者のみ使用できます。")

    elif content.startswith("!status"):
        history = load_history(user_id)
        await message.channel.send(f"💬 現在の会話履歴は {len(history)} 件です。")

    # === LLM会話コマンド ===
    elif content.startswith("!ask "):
        prompt = content[5:]

        # 過去履歴を読み込み
        history = load_history(user_id)
        history.append({"role": "user", "content": prompt})

        try:
            reply = ask_llm(history)
        except Exception as e:
            await message.channel.send(f"❌ エラー: {e}")
            return

        history.append({"role": "assistant", "content": reply})

        # 履歴保存（古いものは切り捨て）
        save_history(user_id, history)

        await message.channel.send(reply)

# === BOT 起動 ===
client.run(DISCORD_TOKEN)