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
            raise ValueError(map(f"Faltan las siguientes variables de entorno: {', '.join(missing)}"))


class TavilyFetcher:
    """Responsable de buscar información fresca y relevante en la web."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = "https://api.tavily.com/search"

    def search_country_news(self, country: str) -> list:
        """Busca hechos, efemérides o noticias relevantes del día para un país."""
        payload = {
            "api_key": self.api_key,
            "query": f"important news events or historical facts today in {country}",
            "search_depth": "advanced",
            "max_results": 3
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
        """Utiliza Gemini para sintetizar los resultados en el formato solicitado."""
        prompt = f"""
        Eres un asistente de noticias diario. Tu tarea es crear un 'Daily Briefing' muy breve y directo utilizando los datos proporcionados.
        
        Datos de México: {json.dumps(mexico_data)}
        Datos de Alemania: {json.dumps(germany_data)}
        
        Formato requerido:
        Genera una o dos secciones breves. Para cada sección usa exactamente esta estructura:
        🌟 **[País]**
        [Hecho o noticia relevante del día redactada de forma amigable]
        🔗 [Enlace] (Usa el enlace original más relevante de los datos aportados, no inventes URLs)
        
        Nota para Alemania: Redacta la explicación en español, pero incluye el término o frase clave original en alemán para ayudar a practicar el idioma (nivel básico/intermedio).
        
        Mantén el mensaje total corto, ideal para leer en menos de 30 segundos en el móvil. No agregues saludos ni despedidas corporativas.
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
            "parse_mode": "Markdown"
        }
        try:
            response = requests.post(self.url, json=payload)
            response.raise_for_status()
            print("¡Daily Briefing enviado con éxito a Telegram!")
        except requests.exceptions.RequestException as e:
            print(f"Error al enviar el mensaje a Telegram: {e}")


def main():
    # 1. Validar configuración
    Config.validate()
    
    # 2. Inicializar servicios
    fetcher = TavilyFetcher(Config.TAVILY_API_KEY)
    generator = BriefingGenerator(Config.GEMINI_API_KEY)
    notifier = TelegramNotifier(Config.TELEGRAM_TOKEN, Config.TELEGRAM_CHAT_ID)
    
    # 3. Ejecutar flujo
    print("Buscando noticias...")
    mx_news = fetcher.search_country_news("Mexico")
    de_news = fetcher.search_country_news("Germany")
    
    print("Sintetizando información...")
    briefing = generator.create_briefing(mx_news, de_news)
    
    print("Enviando notificación...")
    notifier.send(briefing)

if __name__ == "__main__":
    main()
