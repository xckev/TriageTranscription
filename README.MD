# TO RUN APP:
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8000

# URL Request for stations by tag
http://0.0.0.0:8000/stations?tag=(TAG HERE)

http://0.0.0.0:8000/stations will default tag to "police"

# URL Request for audio transcription of about 20 seconds
http://0.0.0.0:8000/transcribe?station_url=(URL HERE)