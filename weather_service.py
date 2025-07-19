import requests

API_KEY = "YOUR_OPENWEATHERMAP_API_KEY"

def get_weather(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&lang=vi&units=metric"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()
    return {
        "desc": data["weather"][0]["description"].capitalize(),
        "temp": int(data["main"]["temp"]),
        "icon": data["weather"][0]["icon"]
    }
