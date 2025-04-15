import json
from datetime import datetime
from openai import OpenAI
import whisper
from supabase import create_client
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable

# Initialize Supabase client
supabase = create_client(
    "https://qnljdbqnskhvkjorvurb.supabase.co",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFubGpkYnFuc2todmtqb3J2dXJiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzgyODk0OTIsImV4cCI6MjA1Mzg2NTQ5Mn0.Joj6eu946k1959uNAENOZ4nDo1nQtgTZ-_cpqBp6hGY"
)

def read_audio_message(audio_file_path):
    # Load Whisper model
    model = whisper.load_model("tiny")
    
    # Transcribe audio file
    result = model.transcribe(audio_file_path)
    return result["text"]

def generate_analysis(dispatch_message):
    # OpenRouter API configuration
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key="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"
    )
    
    prompt = f"""Extract key details from the following dispatcher message and format them exactly as shown below:
{dispatch_message}

Title: [Brief descriptive title of the incident]
Type: 
Location: 
Severity: 
Units Responding: 
Description: 
Timestamp: 
"""

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "YOUR_WEBSITE",
                "X-Title": "Police Scanner Analysis",
            },
            model="deepseek/deepseek-chat:free",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        generated_text = completion.choices[0].message.content
        details = extract_details(generated_text)
        
        print("\n=== Incident Analysis ===")
        print(f"Title: {details.get('Title', 'Unknown')}")
        print(f"Type: {details.get('Type', 'Unknown')}")
        print(f"Location: {details.get('Location', 'Unknown')}")
        print(f"Severity: {details.get('Severity', 'Unknown')}")
        print(f"Units Responding: {details.get('Units Responding', 'Unknown')}")
        print(f"Description: {details.get('Description', 'Unknown')}")
        print(f"Timestamp: {details.get('Timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
        print("=====================")
        
        return details
        
    except Exception as e:
        print(f"Error making API request: {e}")
        return {}

def extract_details(text):
    details = {}
    lines = text.split("\n")
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            details[key.strip()] = value.strip()
    return details

def get_coordinates(location: str):
    """
    Get latitude and longitude coordinates for a given location string.
    Returns (latitude, longitude) tuple or (None, None) if geocoding fails.
    """
    geolocator = Nominatim(user_agent="triage_transcription")
    try:
        location_data = geolocator.geocode(location)
        if location_data:
            return location_data.latitude, location_data.longitude
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Geocoding error for location '{location}': {e}")
    return None, None

def insert_transcription(text: str, analysis: dict, station_url: str):
    """
    Insert transcription data into Supabase database
    """
    # Get coordinates for the location
    location = analysis.get('Location', 'Unknown')
    latitude, longitude = get_coordinates(location)
    
    # Get title from analysis or use first 100 chars of text as fallback
    title = analysis.get('Title', text[:100])
    
    incident_data = {
        'title': title,
        'location': location,
        'type': analysis.get('Type', 'unknown'),
        'severity': 1,  # Default severity since it's not in current analysis
        'latitude': latitude,
        'longitude': longitude,
        'timestamp': datetime.now().isoformat()
    }

    try:
        # Insert the data into the incidents table
        result = supabase.table('incidents').insert(incident_data).execute()
        print(f"Successfully inserted transcription: {result.data}")
        return result.data
    except Exception as e:
        print(f"Error inserting transcription: {e}")
        return None

# Modify the TranscriptionRecord class to use Supabase
class TranscriptionRecord:
    def __init__(self):
        self.transcriptions = []
        self.max_history = 100
        
    def add_transcription(self, text: str, analysis: dict, station_url: str):
        # Store in local memory
        self.transcriptions.append({
            "text": text,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })
        
        # Maintain history limit
        if len(self.transcriptions) > self.max_history:
            self.transcriptions.pop(0)
            
        # Insert into Supabase
        insert_transcription(text, analysis, station_url)

if __name__ == "__main__":
    # Read dispatch message from audio file
    audio_file_path = "test.mp3"
    dispatch_message = read_audio_message(audio_file_path)
    print("\n=== Transcribed Message ===")
    print(dispatch_message)
    print("=====================\n")
    
    # Generate analysis
    analysis = generate_analysis(dispatch_message)
    
    # Create a test station URL (since this is a test file)
    test_station_url = "test_station"
    
    # Insert the transcription into Supabase
    result = insert_transcription(
        text=dispatch_message,
        analysis=analysis,
        station_url=test_station_url
    )
    
    if result:
        print("\n=== Database Insertion Successful ===")
        print(f"Inserted record ID: {result[0]['id'] if result else 'Unknown'}")
    else:
        print("\n=== Database Insertion Failed ===")
