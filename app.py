from fastapi import FastAPI, Query, BackgroundTasks
from radio import get_radio_stations
from transcriber import transcribe_audio_pipeline

app = FastAPI()
active_transcribers = {}

@app.get("/")
def read_root():
  return {"message": "Live Radio Transcription API"}

@app.get("/stations")
def get_stations(tag: str = Query("police", description="any kind of tag")):
  """Fetches radio stations from Radio-Browser API."""
  stations = get_radio_stations(tag)
  return {"stations": stations}

@app.get("/transcribe/start")
async def start_transcription(station_url: str):
    """Starts transcribing a given radio station."""
    if station_url in active_transcribers:
        return {"message": "Transcription already running for this station"}
    
    transcriber = transcribe_audio_pipeline(station_url)
    active_transcribers[station_url] = transcriber
    return {"message": "Transcription started"}

@app.get("/transcribe/stop")
async def stop_transcription(station_url: str):
    """Stops transcribing a given radio station."""
    if station_url in active_transcribers:
        active_transcribers[station_url].stop_streaming()
        del active_transcribers[station_url]
        return {"message": "Transcription stopped"}
    return {"message": "No active transcription found for this station"}