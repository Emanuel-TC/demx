import os
import sys
import requests
import json
import time
from datetime import datetime, timedelta

# Intentar cargar variables desde .env si python-dotenv está instalado
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def _load_env_file(filepath: str = ".env"):
    """Carga variables desde un archivo .env si no están ya en os.environ."""
    if not os.path.isabs(filepath):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        filepath = os.path.join(base_dir, filepath)
    
    if os.path.isfile(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key and key not in os.environ:
                    os.environ[key] = val

_load_env_file()


class Config:
    """Gestiona las credenciales y variables de entorno."""
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    @classmethod
    def validate(cls):
        """Asegura que todas las variables necesarias estén presentes."""
        cls.TAVILY_API_KEY = cls.TAVILY_API_KEY or os.getenv("TAVILY_API_KEY")
        cls.GEMINI_API_KEY = cls.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        cls.TELEGRAM_TOKEN = cls.TELEGRAM_TOKEN or os.getenv("TELEGRAM_TOKEN")
        cls.TELEGRAM_CHAT_ID = cls.TELEGRAM_CHAT_ID or os.getenv("TELEGRAM_CHAT_ID")

        missing = [k for k, v in cls.__dict__.items() if not k.startswith("__") and not v and not callable(v)]
        if missing:
            raise ValueError(f"Faltan las siguientes variables de entorno: {', '.join(missing)}")


class TavilyFetcher:
    """Responsable de buscar efemérides y datos culturales filtrados por la semana actual."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.tavily.com/search"

    def _get_weekly_date_range(self) -> str:
        """Calcula el rango de fechas de los últimos 7 días en inglés."""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        now = datetime.now()
        # Restamos 6 días para abarcar desde el sábado pasado hasta el viernes actual (7 días en total)
        past = now - timedelta(days=6)
        
        start_date = f"{months[past.month - 1]} {past.day}"
        end_date = f"{months[now.month - 1]} {now.day}"
        
        return f"{start_date} and {end_date}"

    def search_country_culture(self, country: str) -> tuple[list, str]:
        """Busca las efemérides y curiosidades históricas más relevantes de la semana."""
        date_range = self._get_weekly_date_range()
        
        # Ampliamos la búsqueda a un rango semanal
        query = f"Most interesting and positive historical events or cultural facts that happened between {date_range} in {country}"
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": 5 # Aumentamos un poco el límite para tener más variedad semanal
        }
        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            return response.json().get("results", []), date_range
        except requests.exceptions.RequestException as e:
            print(f"Error al buscar en Tavily para {country}: {e}")
            return [], date_range


class BriefingGenerator:
    """Responsable de transformar datos crudos en un formato breve, bilingüe y amigable."""
    def __init__(self, api_key: str):
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={api_key}"

    def create_briefing(self, mexico_data: list, germany_data: list, date_range: str, max_retries: int = 3) -> str:
        """Utiliza Gemini para sintetizar los resultados asegurando la coherencia semanal."""
        prompt = f"""
        Eres un curador de contenido cultural e histórico. Tu tarea es crear un 'Weekly Briefing' (Resumen Semanal) fascinante y positivo.
        
        CRÍTICO: Este resumen abarca la semana entre {date_range}. Asegúrate de seleccionar el dato o efeméride más interesante de los proporcionados que haya ocurrido estrictamente en alguna fecha dentro de este rango ({date_range}). No inventes fechas ni repitas datos genéricos.
        
        ESTÁ ESTRICTAMENTE PROHIBIDO incluir noticias amarillistas, políticas de actualidad, tragedias o crímenes.
        
        Datos extraídos para México: {json.dumps(mexico_data)}
        Datos extraídos para Alemania: {json.dumps(germany_data)}
        
        Formato requerido:
        Genera dos secciones. Para cada sección, redacta el contenido primero en español y justo debajo su traducción exacta y natural al inglés.
        Usa estrictamente esta estructura:
        
        🌟 **México (Resumen Semanal)**
        🇪🇸 [Menciona un evento histórico o cultural muy destacado ocurrido en esta semana ({date_range}). Agrega contexto sobre monumentos, calles o su impacto positivo. Tono inspirador y auténtico.]
        🇬🇧 [Traducción al inglés del texto anterior.]
        🔗 [Enlace de la fuente]
        
        🌟 **Alemania (Resumen Semanal)**
        🇪🇸 [Curiosidad cultural o evento destacado de esta semana ({date_range}). Incluye un término clave en alemán y explica su estructura o significado para un estudiante de nivel A1.]
        🇬🇧 [Traducción al inglés del texto anterior. Mantén la palabra clave en alemán y la explicación de su significado.]
        🔗 [Enlace de la fuente]
        
        Mantén el mensaje total corto, ameno y directo al grano. Sin saludos institucionales.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        for attempt in range(max_retries):
            try:
                response = requests.post(self.url, json=payload, headers={"Content-Type": "application/json"})
                response.raise_for_status()
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
                
            except Exception as e:
                print(f"Intento {attempt + 1} fallido al generar el briefing: {e}")
                
                if attempt < max_retries - 1:
                    print("Esperando 5 segundos antes de reintentar...")
                    time.sleep(5)
                else:
                    return f"No se pudo generar el briefing semanal tras {max_retries} intentos debido a un error técnico en la IA."


class TelegramNotifier:
    """Responsable de la entrega del mensaje final."""
    def __init__(self, token: str, chat_id: str):
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"
        self.chat_id = chat_id

    @staticmethod
    def _to_html(text: str) -> str:
        """Convierte Markdown básico generado por la IA a HTML compatible con Telegram."""
        import re
        # Escapar caracteres especiales de HTML
        formatted = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        # Negritas **texto** -> <b>texto</b>
        formatted = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', formatted)
        # Cursivas _texto_ -> <i>texto</i> (sin alterar enlaces o palabras con guión bajo)
        formatted = re.sub(r'(?<!\w)_([^_]+?)_(?!\w)', r'<i>\1</i>', formatted)
        # Enlaces [texto](url) -> <a href="url">texto</a>
        formatted = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2">\1</a>', formatted)
        return formatted

    def send(self, message: str, is_test: bool = False) -> bool:
        """Envía el texto formateado al chat de Telegram usando HTML y con reintento en texto plano."""
        html_message = self._to_html(message)

        payload = {
            "chat_id": self.chat_id,
            "text": html_message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }

        try:
            response = requests.post(self.url, json=payload)
            res_json = response.json() if response.content else {}

            if response.status_code == 200 and res_json.get("ok"):
                if is_test:
                    print("✓ Mensaje de prueba enviado con éxito a Telegram.")
                else:
                    print("¡Weekly Briefing enviado con éxito a Telegram!")
                return True

            error_desc = res_json.get("description", response.text)
            print(f"Error al enviar el mensaje a Telegram ({response.status_code}): {error_desc}")

            # Si el error se debe a problemas de formato en Telegram, reintentar en texto plano
            if "can't parse entities" in error_desc.lower() or "entity" in error_desc.lower():
                print("Reintentando envío como texto plano (sin parse_mode)...")
                fallback_payload = {
                    "chat_id": self.chat_id,
                    "text": message,
                    "disable_web_page_preview": True
                }
                fb_res = requests.post(self.url, json=fallback_payload)
                fb_json = fb_res.json() if fb_res.content else {}
                if fb_res.status_code == 200 and fb_json.get("ok"):
                    if is_test:
                        print("✓ Mensaje de prueba enviado con éxito a Telegram (como texto plano).")
                    else:
                        print("¡Weekly Briefing enviado con éxito a Telegram (como texto plano)!")
                    return True
                print(f"Error en el reintento: {fb_json.get('description', fb_res.text)}")

            if "chat not found" in error_desc.lower():
                print("\n💡 Tip: Abre tu bot en Telegram y pulsa 'Iniciar' (/start). Los bots no pueden enviar mensajes a usuarios que no hayan interactuado previamente con ellos.")

            return False

        except requests.exceptions.RequestException as e:
            print(f"Error de conexión con la API de Telegram: {e}")
            return False

    def test_connection(self) -> bool:
        """Prueba que la conexión y el envío de mensajes al chat funcionen correctamente."""
        test_msg = "🤖 <b>Test de conexión</b>: Conexión con el bot de Telegram establecida con éxito. ¡Listo para generar el briefing!"
        return self.send(test_msg, is_test=True)


def main():
    Config.validate()
    
    notifier = TelegramNotifier(Config.TELEGRAM_TOKEN, Config.TELEGRAM_CHAT_ID)
    
    # Si se pasa el argumento --test, solo probamos la conexión y salimos
    if "--test" in sys.argv:
        print("Modo de verificación: Comprobando conexión y envío con Telegram...")
        if notifier.test_connection():
            print("Verificación completada: Telegram funciona correctamente.")
        else:
            print("La verificación ha fallado. Revisa tu configuración o credenciales.")
        return

    # 1. Probar primero que se pueden enviar mensajes antes de gastar cuotas en Tavily o Gemini
    print("Verificando envío de mensajes a Telegram antes de iniciar la búsqueda...")
    if not notifier.test_connection():
        print("\nCancelando ejecución: No se pudo enviar el mensaje a Telegram. No se consultarán Tavily ni Gemini.")
        return

    fetcher = TavilyFetcher(Config.TAVILY_API_KEY)
    generator = BriefingGenerator(Config.GEMINI_API_KEY)

    print("\nBuscando los eventos más destacados de la semana...")
    mx_news, date_range = fetcher.search_country_culture("Mexico")
    de_news, _ = fetcher.search_country_culture("Germany")
    
    print(f"Sintetizando información semanal para el rango: {date_range}...")
    briefing = generator.create_briefing(mx_news, de_news, date_range)
    
    print("Enviando notificación del briefing a Telegram...")
    notifier.send(briefing)

if __name__ == "__main__":
    main()