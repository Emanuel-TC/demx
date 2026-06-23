import os
import requests
import json

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
    """Responsable de buscar efemérides y datos culturales en la web."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.tavily.com/search"

    def search_country_culture(self, country: str) -> list:
        """Busca efemérides, curiosidades y eventos históricos positivos del día."""
        # Cambiamos la búsqueda para evitar noticias duras y buscar cultura/historia
        query = f"On this day positive historical events, cultural facts, or interesting curiosities today in {country}"
        
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": 4 # Aumentamos un poco para darle más opciones a Gemini
        }
        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            return response.json().get("results", [])
        except requests.exceptions.RequestException as e:
            print(f"Error al buscar en Tavily para {country}: {e}")
            return []


class BriefingGenerator:
    """Responsable de transformar datos crudos en un formato breve y amigable."""
    def __init__(self, api_key: str):
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    def create_briefing(self, mexico_data: list, germany_data: list) -> str:
        """Utiliza Gemini para sintetizar los resultados enfocándose en historia y cultura."""
        prompt = f"""
        Eres un curador de contenido cultural e histórico. Tu tarea es crear un 'Daily Briefing' breve, fascinante y positivo. 
        ESTÁ ESTRICTAMENTE PROHIBIDO incluir noticias amarillistas, políticas de actualidad, tragedias o crímenes.
        
        Datos extraídos para México: {json.dumps(mexico_data)}
        Datos extraídos para Alemania: {json.dumps(germany_data)}
        
        Formato requerido:
        Genera dos secciones breves. Para cada sección usa esta estructura:
        
        🌟 **México**
        [Menciona qué efeméride se conmemora hoy o un dato histórico/cultural muy curioso basado en los datos. Agrega contexto interesante: menciona si hay un monumento, una calle, una plaza, o cómo este hecho impactó la historia de forma positiva. Usa un tono inspirador y conversacional.]
        🔗 [Enlace de la fuente]
        
        🌟 **Alemania**
        [Comparte una curiosidad cultural, un evento histórico positivo o un dato de interés del día. 
        Redacta la explicación en español, pero incluye el término o frase clave original en alemán. Asegúrate de explicar la estructura o el significado literal de esa palabra en alemán de forma muy sencilla, pensada para alguien con un nivel A1 que está empezando a aprender el idioma.]
        🔗 [Enlace de la fuente]
        
        Mantén el mensaje total corto, ameno y directo al grano.
        """
        
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        
        try:
            response = requests.post(self.url, json=payload, headers={"Content-Type": "application/json"})
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            print(f"Error al generar el briefing con Gemini: {e}")
            return "No se pudo generar el briefing diario debido a un error técnico."


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
            "disable_web_page_preview": True # Desactiva las vistas previas gigantes de los links
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
    
    print("Buscando efemérides y curiosidades...")
    # Llamamos al nuevo método enfocado en cultura
    mx_news = fetcher.search_country_culture("Mexico")
    de_news = fetcher.search_country_culture("Germany")
    
    print("Sintetizando información...")
    briefing = generator.create_briefing(mx_news, de_news)
    
    print("Enviando notificación a Telegram...")
    notifier.send(briefing)

if __name__ == "__main__":
    main()
