from fastapi import FastAPI, Query
from radio import get_radio_stations
from transcriber import transcribe_audio_pipeline

app = FastAPI()

@app.get("/")
def read_root():
  return {"message": "Live Radio Transcription API"}

@app.get("/stations")
def get_stations(tag: str = Query("police", description="any kind of tag")):
  """Fetches radio stations from Radio-Browser API."""
  stations = get_radio_stations(tag)
  return {"stations": stations}

@app.get("/transcribe")
def get_transcription(station_url: str):
  """Transcribes a given radio station."""
  transcription = transcribe_audio_pipeline(station_url)
  print(transcription)
  return {"transcription": transcription}