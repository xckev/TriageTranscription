from io import BytesIO
import requests
import whisper
from pydub import AudioSegment
import time
import io
import threading
import queue
from config import MODEL_SIZE
from openai import OpenAI
from datetime import datetime
from typing import Dict

# Load Whisper model
model = whisper.load_model(MODEL_SIZE)

class LiveTranscriber:
    def __init__(self, chunk_duration=10):
        self.audio_queue = queue.Queue()
        self.is_running = False
        self.chunk_duration = chunk_duration  # Duration in seconds
        self.buffer = io.BytesIO()
        self.current_chunk_start = time.time()

    def start_streaming(self, url):
        self.is_running = True
        
        # Start stream capture thread
        stream_thread = threading.Thread(target=self._capture_stream, args=(url,))
        stream_thread.daemon = True
        stream_thread.start()
        
        # Start transcription thread
        transcribe_thread = threading.Thread(target=self._process_audio)
        transcribe_thread.daemon = True
        transcribe_thread.start()
        
        return stream_thread, transcribe_thread

    def stop_streaming(self):
        self.is_running = False

    def _capture_stream(self, url):
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            for chunk in response.iter_content(chunk_size=1024):
                if not self.is_running:
                    break
                    
                self.buffer.write(chunk)
                
                # Check if we've captured enough audio
                if time.time() - self.current_chunk_start >= self.chunk_duration:
                    # Process the current buffer
                    self.buffer.seek(0)
                    audio = AudioSegment.from_file(self.buffer, format="mp3")
                    self.audio_queue.put(audio)
                    
                    # Reset buffer and timer
                    self.buffer = io.BytesIO()
                    self.current_chunk_start = time.time()
                    
        except requests.RequestException as e:
            print(f"Error in stream capture: {e}")
            self.is_running = False

    def _process_audio(self):
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key="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"  # Move this to config.py
        )
        
        while self.is_running:
            try:
                audio = self.audio_queue.get(timeout=1)
                audio = self._preprocess_audio(audio)
                
                temp_file = "temp_chunk.wav"
                audio.export(temp_file, format="wav")
                
                # Transcribe
                result = model.transcribe(temp_file)
                transcribed_text = result["text"].strip()
                
                if transcribed_text:
                    # Generate analysis
                    analysis = self._analyze_dispatch(client, transcribed_text)
                    
                    # Only process if we have valid analysis
                    if analysis:
                        # Send to callback if provided
                        if hasattr(self, 'callback') and self.callback:
                            self.callback(transcribed_text, analysis)
                        
                        print(f"Transcription: {transcribed_text}")
                        print("Analysis:", analysis)
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in audio processing: {e}")

    def _analyze_dispatch(self, client, dispatch_message):
        # Get recent history if available
        recent_history = ""
        if hasattr(self, 'callback') and hasattr(self.callback, '__self__'):
            record_keeper = self.callback.__self__
            if hasattr(record_keeper, 'transcriptions'):
                # Get last 3 transcriptions for context
                recent = record_keeper.transcriptions[-3:] if record_keeper.transcriptions else []
                recent_history = "\n".join([t["text"] for t in recent])

        prompt = f"""Analyze this emergency dispatch message. Include previous context if relevant.
If this is not an emergency or disaster-related incident, respond with 'NOT_EMERGENCY'.

Previous context (if relevant):
{recent_history}

Current message:
{dispatch_message}

Format the response exactly as shown below:
Type: [Specific type of emergency/incident]
Location: [Exact location including address if available]
Severity: [Critical/High/Medium/Low]
Units Responding: [List all responding units]
Description: [Detailed description of the emergency]
Timestamp: [Current time]

Debug Info:
- Confidence: [High/Medium/Low]
- Reasoning: [Brief explanation of emergency classification]
"""

        try:
            print("\n=== Processing New Dispatch ===")
            print(f"Message: {dispatch_message}")
            
            completion = client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "YOUR_WEBSITE",
                    "X-Title": "Emergency Dispatch Analysis",
                },
                model="deepseek/deepseek-chat:free",
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            generated_text = completion.choices[0].message.content
            print(f"\nAI Response:\n{generated_text}")
            
            # Check if it's not an emergency
            if "NOT_EMERGENCY" in generated_text:
                print("Result: Not an emergency - skipping")
                return None
            
            # Extract and validate the analysis
            analysis = self._extract_details(generated_text)
            is_valid, message = self._validate_analysis(analysis)
            
            if not is_valid:
                print(f"Validation Failed: {message}")
                return None
            
            # Add timestamp if missing
            if 'Timestamp' not in analysis:
                analysis['Timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Add debug info
            analysis['Debug'] = {
                'Confidence': analysis.get('Confidence', 'Unknown'),
                'Reasoning': analysis.get('Reasoning', 'Unknown'),
                'ValidationStatus': message
            }
            
            print("\nValidated Analysis:")
            for key, value in analysis.items():
                print(f"{key}: {value}")
            print("===========================\n")
            
            return analysis
            
        except Exception as e:
            print(f"Error in analysis: {e}")
            return None

    def _extract_details(self, text):
        details = {}
        lines = text.split("\n")
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                details[key.strip()] = value.strip()
        return details

    def _preprocess_audio(self, audio):
        # Convert to mono
        audio = audio.set_channels(1)
        # Normalize volume
        audio = audio.apply_gain(-audio.max_dBFS)
        # Resample to 16kHz
        audio = audio.set_frame_rate(16000)
        return audio

    def _validate_analysis(self, analysis: Dict) -> tuple[bool, str]:
        # Required fields that must be present and non-empty
        required_fields = ['Type', 'Location', 'Severity', 'Units Responding', 'Description']
        
        validation_results = []
        
        # Check for missing or empty fields
        for field in required_fields:
            if field not in analysis:
                validation_results.append(f"Missing field: {field}")
            elif not analysis[field].strip():
                validation_results.append(f"Empty field: {field}")
        
        if validation_results:
            return False, "; ".join(validation_results)
        
        # Validate severity levels
        valid_severities = ['critical', 'high', 'medium', 'low']
        if analysis['Severity'].lower() not in valid_severities:
            return False, f"Invalid severity level: {analysis['Severity']}"
        
        # List of keywords indicating disasters/emergencies
        emergency_keywords = [
            'fire', 'explosion', 'crash', 'accident', 'disaster', 'emergency',
            'injury', 'casualty', 'damage', 'hazard', 'threat', 'danger',
            'evacuation', 'rescue', 'critical', 'severe', 'major', 'incident',
            'medical', 'assault', 'shooting', 'crime', 'violence'
        ]
        
        # Check if the content is related to an emergency
        description_lower = analysis['Description'].lower()
        type_lower = analysis['Type'].lower()
        
        is_emergency = any(keyword in description_lower or keyword in type_lower 
                          for keyword in emergency_keywords)
        
        if not is_emergency:
            return False, f"Not emergency-related. Type: {analysis['Type']}, Description contains no emergency keywords"
        
        return True, "Valid emergency analysis"

def get_audio_stream(url, output_file="radio.wav"):
  """
  Captures 10 seconds of live radio audio from the given URL and saves it as a WAV file.
  
  :param url: The streaming URL of the radio station.
  :param output_file: The name of the output WAV file.
  """
  try:
    # Open a connection to the stream
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Ensure the request was successful

    buffer = BytesIO()  # Create an in-memory buffer
    chunk_size = 1024  # Read in small chunks

    start_time = time.time()
    # Read stream into buffer
    for chunk in response.iter_content(chunk_size=chunk_size):
      buffer.write(chunk)

      if time.time() - start_time >= 5:
        break  # Stop after capturing the required duration

    # Convert raw stream data to an AudioSegment
    buffer.seek(0)  # Reset buffer position
    audio = AudioSegment.from_file(buffer, format="MP3")  # Most streams are MP3

    # Export as WAV
    audio.export(output_file, format="wav")
    print(f"Saved 10 seconds of audio to {output_file}")

  except requests.RequestException as e:
    print(f"Error fetching audio stream: {e}")

def preprocess_audio(input_path, output_path="processed_audio.wav"):
  """
  Preprocess the audio file:
  1. Convert to mono
  2. Normalize volume
  3. Trim silence
  4. Resample to 16kHz
  """
  # Load audio
  audio = AudioSegment.from_file(input_path)

  # Convert to mono
  audio = audio.set_channels(1)

  # Normalize volume
  audio = audio.apply_gain(-audio.max_dBFS)

  # Resample to 16kHz
  processed_audio = audio.set_frame_rate(16000)

  # Export the processed audio
  processed_audio.export(output_path, format="wav")

  return output_path

def transcribe_audio(file_path: str):
  """
  Transcribes the audio from a WAV file using Whisper.
  """
  result = model.transcribe(file_path)
  return result["text"]

def transcribe_audio_pipeline(station_url):
    """
    Main function to continuously transcribe audio from a radio station.
    Returns a LiveTranscriber instance that can be controlled.
    """
    transcriber = LiveTranscriber()
    transcriber.start_streaming(station_url)
    return transcriber