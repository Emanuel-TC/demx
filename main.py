import os
import requests
import json
import time
from datetime import datetime, timedelta

class Config:
    """Gestiona las credenciales y variables de entorno."""
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    @classmethod
    def validate(cls):
        """Asegura que todas las variables necesarias estén presentes."""
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
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

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

    def send(self, message: str):
        """Envía el texto formateado al chat de Telegram usando Markdown."""
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            print("¡Weekly Briefing enviado con éxito a Telegram!")
        except requests.exceptions.RequestException as e:
            print(f"Error al enviar el mensaje a Telegram: {e}")


def main():
    Config.validate()
    
    fetcher = TavilyFetcher(Config.TAVILY_API_KEY)
    generator = BriefingGenerator(Config.GEMINI_API_KEY)
    notifier = TelegramNotifier(Config.TELEGRAM_TOKEN, Config.TELEGRAM_CHAT_ID)
    
    print("Buscando los eventos más destacados de la semana...")
    mx_news, date_range = fetcher.search_country_culture("Mexico")
    de_news, _ = fetcher.search_country_culture("Germany")
    
    print(f"Sintetizando información semanal para el rango: {date_range}...")
    briefing = generator.create_briefing(mx_news, de_news, date_range)
    
    print("Enviando notificación a Telegram...")
    notifier.send(briefing)

if __name__ == "__main__":
    main()