import whisper
from pydub import AudioSegment
import os
from config import MODEL_SIZE

model = whisper.load_model(MODEL_SIZE)  # Change to "small", "medium", "large" if needed

def transcribe_audio(file_path: str):
  """
  Transcribes the audio from a WAV file using Whisper.
  """
  result = model.transcribe(file_path)
  return result["text"]

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

# Example usage
if __name__ == "__main__":
  file_path = "radiochatter.wav"  # Change this to your file name

  # Preprocess the audio
  processed_file = preprocess_audio(file_path)
  print(f"Processed audio saved to: {processed_file}")

  # Transcribe the audio
  transcription = transcribe_audio(processed_file)
  print("Transcription:", transcription)

