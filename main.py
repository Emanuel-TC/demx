import os
import requests
import json
import time
from datetime import datetime

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
    """Responsable de buscar efemérides y datos culturales filtrados por la fecha actual."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.tavily.com/search"

    def _get_current_date_str(self) -> str:
        """Calcula el día y mes actual en inglés para optimizar la búsqueda."""
        months = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]
        now = datetime.now()
        # Nota: Al ejecutarse a las 04:23 UTC / 06:23 CEST, coincide perfectamente en el mismo día calendario.
        return f"{months[now.month - 1]} {now.day}"

    def search_country_culture(self, country: str) -> tuple[list, str]:
        """Busca efemérides y curiosidades históricas estrictamente vinculadas al día de hoy."""
        date_str = self._get_current_date_str()
        
        # Anclamos la búsqueda exigiendo que ocurra específicamente en la fecha de hoy
        query = f"Historical events, cultural facts, or positive curiosities happening specifically on {date_str} in {country}"
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": 4
        }
        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            return response.json().get("results", []), date_str
        except requests.exceptions.RequestException as e:
            print(f"Error al buscar en Tavily para {country}: {e}")
            return [], date_str


class BriefingGenerator:
    """Responsable de transformar datos crudos en un formato breve, bilingüe y amigable."""
    def __init__(self, api_key: str):
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    def create_briefing(self, mexico_data: list, germany_data: list, date_str: str, max_retries: int = 3) -> str:
        """Utiliza Gemini para sintetizar los resultados asegurando la coherencia con la fecha actual y formato bilingüe."""
        prompt = f"""
        Eres un curador de contenido cultural e histórico. Tu tarea es crear un 'Daily Briefing' breve, fascinante y positivo.
        
        CRÍTICO: Hoy es exactamente {date_str}. Asegúrate de que las efemérides o datos seleccionados correspondan a los eventos celebrados o acontecidos en este día específico ({date_str}). Descarta cualquier resultado que pertenezca a otra fecha o que sea un resumen general de noticias actuales.
        
        ESTÁ ESTRICTAMENTE PROHIBIDO incluir noticias amarillistas, políticas de actualidad, tragedias o crímenes.
        
        Datos extraídos para México: {json.dumps(mexico_data)}
        Datos extraídos para Alemania: {json.dumps(germany_data)}
        
        Formato requerido:
        Genera dos secciones. Para cada sección, redacta el contenido primero en español y justo debajo su traducción exacta y natural al inglés.
        Usa estrictamente esta estructura:
        
        🌟 **México**
        🇪🇸 [Menciona qué efeméride se conmemora hoy ({date_str}) o un dato histórico/cultural curioso de esa fecha. Agrega contexto sobre monumentos, calles o impacto positivo. Tono inspirador.]
        🇬🇧 [Traducción al inglés del texto anterior.]
        🔗 [Enlace de la fuente]
        
        🌟 **Alemania**
        🇪🇸 [Curiosidad cultural o evento de este día ({date_str}). Incluye el término original en alemán y explica su estructura o significado para un estudiante de nivel A1.]
        🇬🇧 [Traducción al inglés del texto anterior. Mantén la palabra clave en alemán y la explicación de su significado.]
        🔗 [Enlace de la fuente]
        
        Mantén el mensaje total corto, ameno y directo al grano. Sin saludos institucionales.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        # Bucle de reintentos
        for attempt in range(max_retries):
            try:
                response = requests.post(self.url, json=payload, headers={"Content-Type": "application/json"})
                response.raise_for_status()
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            
            except Exception as e:
                print(f"Intento {attempt + 1} fallido al generar el briefing: {e}")
                
                # Si no es el último intento, espera 5 segundos antes de volver a probar
                if attempt < max_retries - 1:
                    print("Esperando 5 segundos antes de reintentar...")
                    time.sleep(5)
                else:
                    return f"No se pudo generar el briefing diario tras {max_retries} intentos debido a un error técnico en la IA."


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
            print("¡Daily Briefing enviado con éxito a Telegram!")
        except requests.exceptions.RequestException as e:
            print(f"Error al enviar el mensaje a Telegram: {e}")


def main():
    Config.validate()
    
    fetcher = TavilyFetcher(Config.TAVILY_API_KEY)
    generator = BriefingGenerator(Config.GEMINI_API_KEY)
    notifier = TelegramNotifier(Config.TELEGRAM_TOKEN, Config.TELEGRAM_CHAT_ID)
    
    print("Buscando efemérides del día...")
    mx_news, date_str = fetcher.search_country_culture("Mexico")
    de_news, _ = fetcher.search_country_culture("Germany")
    
    print(f"Sintetizando información para la fecha: {date_str}...")
    briefing = generator.create_briefing(mx_news, de_news, date_str)
    
    print("Enviando notificación a Telegram...")
    notifier.send(briefing)

if __name__ == "__main__":
    main()