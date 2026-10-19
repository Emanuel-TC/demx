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
                v = v.strip().strip("'\"")
                if k and k not in os.environ:
                    os.environ[k] = v

_load_env_fallback()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


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

        return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión al enviar el mensaje: {e}")
        return False


if __name__ == "__main__":
    test_telegram_connection()

