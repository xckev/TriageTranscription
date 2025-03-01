from fastapi import FastAPI, Query, BackgroundTasks
from radio import get_radio_stations
from transcriber import transcribe_audio_pipeline
from datetime import datetime
from openai import OpenAI
from typing import List, Dict
import queue

app = FastAPI()
active_transcribers = {}
transcription_records = {}

class TranscriptionRecord:
    def __init__(self):
        self.transcriptions: List[Dict] = []
        self.max_history = 100  # Keep last 100 transcriptions
        self.analysis_queue = queue.Queue()
        
    def add_transcription(self, text: str, analysis: Dict):
        self.transcriptions.append({
            "text": text,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })
        # Maintain history limit
        if len(self.transcriptions) > self.max_history:
            self.transcriptions.pop(0)

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
    
    # Create record keeper for this station
    if station_url not in transcription_records:
        transcription_records[station_url] = TranscriptionRecord()
    
    # Create callback for handling transcriptions
    def handle_transcription(text: str, analysis: Dict):
        transcription_records[station_url].add_transcription(text, analysis)
    
    transcriber = transcribe_audio_pipeline(station_url)
    transcriber.callback = handle_transcription
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

@app.get("/transcribe/history")
async def get_transcription_history(station_url: str):
    """Gets transcription history for a station."""
    if station_url not in transcription_records:
        return {"message": "No transcription history found for this station"}
    
    return {
        "station_url": station_url,
        "history": transcription_records[station_url].transcriptions
    }