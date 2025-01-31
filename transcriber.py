from io import BytesIO
import requests
import whisper
from pydub import AudioSegment
import time
from config import MODEL_SIZE

# Load Whisper model
model = whisper.load_model(MODEL_SIZE)

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
  Main function to capture, preprocess, and transcribe audio from a radio station.
  """
  # Step 1: Capture audio stream
  get_audio_stream(station_url)

  # Step 2: Preprocess the captured audio
  processed_file = preprocess_audio("radio.wav")

  # Step 3: Transcribe the preprocessed audio
  transcription = transcribe_audio(processed_file)

  return transcription