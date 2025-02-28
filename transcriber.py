from io import BytesIO
import requests
import whisper
from pydub import AudioSegment
import time
import io
import threading
import queue
from config import MODEL_SIZE

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
        while self.is_running:
            try:
                # Get audio chunk from queue
                audio = self.audio_queue.get(timeout=1)
                
                # Preprocess audio
                audio = self._preprocess_audio(audio)
                
                # Save temporary file for Whisper
                temp_file = "temp_chunk.wav"
                audio.export(temp_file, format="wav")
                
                # Transcribe
                result = model.transcribe(temp_file)
                if result["text"].strip():  # Only print non-empty transcriptions
                    print(f"Transcription: {result['text']}")
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in audio processing: {e}")

    def _preprocess_audio(self, audio):
        # Convert to mono
        audio = audio.set_channels(1)
        # Normalize volume
        audio = audio.apply_gain(-audio.max_dBFS)
        # Resample to 16kHz
        audio = audio.set_frame_rate(16000)
        return audio

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