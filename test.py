import json
from datetime import datetime
from openai import OpenAI
import whisper

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
        
        # print(completion)
        
        generated_text = completion.choices[0].message.content
        # print(generated_text)
        
        details = extract_details(generated_text)
        
        print("\n=== Incident Analysis ===")
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

if __name__ == "__main__":
    # Read dispatch message from audio file
    audio_file_path = "test.mp3"
    dispatch_message = read_audio_message(audio_file_path)
    print("\n=== Transcribed Message ===")
    print(dispatch_message)
    print("=====================\n")
    # dispatch_message = """
    # Dispatcher, all units, we have a 10 to 31 in progress at 2457 Oakwood Drive. Armed robbery at a convenience store. Suspects are two males, both wearing black hoodies and masks. Witnesses report one is armed with a handgun. Approach with caution. Over. Unit 14, copy that Dispatch. Unit 14 responding, ETA 3 minutes. Any surveillance footage available? Over. Dispatcher. Affirmative. Store security cameras are active. We're pulling footage now. Suspects fled on foot towards Maple Avenue. Over. Unit 22. Dispatch, this is Unit 22. We're setting up a perimeter at Maple and 3rd. Do we have K9 support en route? Over. Dispatcher. Affirmative. K9 Unit 5 is rolling out now. Estimated two minutes out. Over. Unit 14, 10 to 4 approaching scene now. No visual on suspects yet. We'll update. Over. Dispatcher. Copy that. All units maintain caution. Suspects considered armed and dangerous. Over.
    # """
    
    generate_analysis(dispatch_message)
