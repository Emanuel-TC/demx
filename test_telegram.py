import os
import requests
from datetime import datetime

# 1. Cargar variables desde .env (soporta python-dotenv y fallback nativo)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _load_env_fallback(filepath: str = ".env"):
    if not os.path.isabs(filepath):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_dir, filepath)
    if os.path.isfile(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                # Eliminar comentarios en línea
                if "#" in v:
                    v = v.split("#", 1)[0]
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v

_load_env_fallback()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
if TELEGRAM_CHAT_ID and "#" in TELEGRAM_CHAT_ID:
    TELEGRAM_CHAT_ID = TELEGRAM_CHAT_ID.split("#", 1)[0].strip()


def test_telegram_connection():
    print("=" * 60)
    print("🤖 TEST DE CONEXIÓN CON TELEGRAM BOT")
    print("=" * 60)

    # Paso 1: Validar credenciales locales
    print("\n[1/3] Verificando credenciales en .env...")
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        missing = []
        if not TELEGRAM_TOKEN:
            missing.append("TELEGRAM_TOKEN")
        if not TELEGRAM_CHAT_ID:
            missing.append("TELEGRAM_CHAT_ID")
        print(f"❌ Error: Faltan las siguientes variables en .env: {', '.join(missing)}")
        return False

    masked_token = f"{TELEGRAM_TOKEN[:9]}...{TELEGRAM_TOKEN[-5:]}" if len(TELEGRAM_TOKEN) > 15 else "***"
    print(f"  • Token:   {masked_token}")
    print(f"  • Chat ID: {TELEGRAM_CHAT_ID}")

    # Paso 2: Verificar token con getMe
    print("\n[2/3] Verificando token con Telegram (getMe)...")
    get_me_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
    try:
        res = requests.get(get_me_url, timeout=10)
        data = res.json()
        if not (res.status_code == 200 and data.get("ok")):
            print(f"❌ Error al validar token ({res.status_code}): {data.get('description', res.text)}")
            if res.status_code == 401:
                print("💡 Tip: Revisa que TELEGRAM_TOKEN sea exactamente el que te proporcionó @BotFather.")
            return False

        bot_info = data.get("result", {})
        bot_name = bot_info.get("first_name", "Bot")
        bot_username = bot_info.get("username", "desconocido")
        print(f"  ✓ Bot verificado: {bot_name} (@{bot_username})")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de red al contactar a Telegram: {e}")
        return False

    # Paso 3: Enviar mensaje 'Hola mundo' chulo
    print("\n[3/3] Enviando mensaje '¡Hola Mundo!' al chat...")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cool_message = f"""🚀 <b>¡Hola Mundo Telegram!</b> 🤖

✨ <i>Conexión establecida con éxito entre tu entorno local y el bot.</i>

📊 <b>Detalles de la sesión:</b>
• <b>Bot:</b> {bot_name} (@{bot_username})
• <b>Chat ID:</b> <code>{TELEGRAM_CHAT_ID}</code>
• <b>Fecha y hora:</b> <code>{now_str}</code>
• <b>Estado:</b> 🟢 <i>Online y listo para recibir los briefings</i>

⚡ <i>¡Todo listo para despegar!</i> 🎉"""

    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": cool_message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        send_res = requests.post(send_url, json=payload, timeout=10)
        send_data = send_res.json() if send_res.content else {}

        if send_res.status_code == 200 and send_data.get("ok"):
            print("  ✓ ¡Mensaje enviado con éxito! Revisa tu aplicación de Telegram.")
            print("\n" + "=" * 60)
            print("🎉 ¡TODO FUNCIONA CORRECTAMENTE!")
            print("=" * 60)
            return True

        error_desc = send_data.get("description", send_res.text)
        print(f"❌ Error al enviar el mensaje ({send_res.status_code}): {error_desc}")

        if "chat not found" in error_desc.lower():
            print(f"\n💡 TIP CRÍTICO: Abre Telegram, busca tu bot @{bot_username} y pulsa el botón 'Iniciar' (o escribe /start).")
            print("   Los bots de Telegram no tienen permiso para enviar mensajes a un usuario hasta que el usuario inicia la conversación.")
        elif "bot was blocked by the user" in error_desc.lower():
            print(f"\n💡 Tip: El bot @{bot_username} está bloqueado en tu cuenta. Desbloquéalo para recibir mensajes.")
        elif "the bot can't send messages to the bot" in error_desc.lower():
            print(f"\n💡 EXPLICACIÓN DEL ERROR:")
            print(f"   Has puesto como Chat ID el número '{TELEGRAM_CHAT_ID}', que es el ID del propio bot (@{bot_username}).")
            print("   ¡Un bot de Telegram no puede enviarse mensajes a sí mismo!")
            print("\n📌 Recuerda que los IDs de grupos en Telegram SIEMPRE empiezan por signo menos '-' o '-100'.")
            
            try:
                updates_res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates", timeout=5).json()
                found_groups = {}
                for upd in updates_res.get("result", []):
                    msg = upd.get("message") or upd.get("my_chat_member", {})
                    chat = msg.get("chat", {})
                    if chat.get("type") in ("group", "supergroup"):
                        found_groups[chat.get("id")] = chat.get("title", "Sin título")
                
                if found_groups:
                    print("\n🔎 ¡Encontramos estos grupos en la actividad reciente del bot!:")
                    for gid, gtitle in found_groups.items():
                        print(f"   👉 Grupo: '{gtitle}'  -->  TELEGRAM_CHAT_ID={gid}")
                else:
                    print("\n📌 Pasos para obtener el ID de tu grupo:")
                    print(f"   1. Añade a @{bot_username} a tu grupo de Telegram.")
                    print("   2. Escribe cualquier mensaje en el grupo (ej. 'hola').")
                    print(f"   3. Abre en tu navegador este enlace:")
                    print(f"      https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates")
                    print("   4. Busca '\"chat\":{\"id\": -...' y copia ese número negativo en tu .env.")
            except Exception:
                pass

        return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión al enviar el mensaje: {e}")
        return False


if __name__ == "__main__":
    test_telegram_connection()

