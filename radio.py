import httpx
from config import RADIO_BROWSER_API, DEFAULT_TAG

def get_radio_stations(tag=DEFAULT_TAG, limit=15):
  """Fetches police scanner radio stations from Radio-Browser API."""
  params = {
    "limit": limit,
    "hidebroken": True
  }

  url = RADIO_BROWSER_API + tag
  print(url)
  
  response = httpx.get(url, params=params)
  if response.status_code == 200:
    stations = response.json()
    return [{"name": s["name"], "url": s["url_resolved"]} for s in stations]
  else:
    return []