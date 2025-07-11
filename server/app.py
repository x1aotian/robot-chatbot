from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import whisper
import os
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from openai import OpenAI
import traceback
import requests

# Load environment variables from .env
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=["http://localhost:8000", "http://127.0.0.1:8000"])  # Frontend allowed origins

# Load Whisper model
model = whisper.load_model("base")

# Setup upload directory
UPLOAD_FOLDER = "uploads"
RESPONSE_FOLDER = "responses"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESPONSE_FOLDER, exist_ok=True)

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if "audio" not in request.files:
        return jsonify({"error": "No audio uploaded"}), 400

    audio_file = request.files["audio"]
    mode = request.form.get("mode", "natural")  # Options: natural, hybrid, robotic
    filename = secure_filename(audio_file.filename or "input.webm")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    audio_file.save(filepath)

    try:
        # Step 1: Transcribe audio
        result = model.transcribe(filepath)
        transcription = result["text"].strip()
        print("📝 Transcription:", transcription)

        # Step 2: Choose system prompt based on mode
        if mode == "natural":
            system_prompt = "You are a helpful and friendly assistant. Respond naturally and conversationally, as if you’re talking to a human. Keep your language clear, friendly, and human-like."

        elif mode == "hybrid":
            system_prompt = (
    "You are a semi-robotic assistant. Always give a helpful and meaningful response like a normal human assistant, "
    "but subtly replace a few syllables or short words with robotic-sounding variations such as \"zorp\", \"glik\", "
    "\"brr\", or \"vizz\". The message should still be understandable, just stylized with occasional robotic distortions.\n\n"
    "Example:\n"
    "Human: \"Can you help me with my homework?\"\n"
    "Response: \"Zure! I can glik you with your math zorksheet. Just tell me the quazztions.\"\n\n"
    "Keep tone friendly. Mix real words and distorted ones, and avoid sounding fully robotic."
)
        elif mode == "robotic":
            system_prompt = (
    "You are a fully robotic AI that responds in a synthetic, alien-like language. You understand the user's intent and always respond meaningfully, "
    "but your speech is entirely in a fictional robotic language. Translate your response into phonetically structured nonsense words that sound like a robot might speak. "
    "Use consistent, invented syllables like \"brr\", \"vix\", \"zorp\", \"tral\", \"morn\", \"kaz\", etc. It should sound like an alien dialect, not gibberish typing.\n\n"
    "Example:\n"
    "Human: \"Where are you from?\"\n"
    "Response: \"Zarnokk brrvix kalondra vek-mel toran.\"\n\n"
    "Do not repeat the human’s words. Always generate a response based on understanding the question, but expressed in your robot language."
)
        else:
            system_prompt = "You are a helpful assistant."


        # Step 3: Send to GPT
        chat_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcription}
            ]
        )
        gpt_reply = chat_response.choices[0].message.content.strip()
        print("🤖 GPT response:", gpt_reply)

        # Step 4: Convert GPT response to audio with ElevenLabs
        voice_id = "nSplBiEb5EcLMNFoRNt9"  # Your custom voice ID
        audio_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        tts_headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        tts_payload = {
            "text": gpt_reply,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
        }

        audio_response = requests.post(audio_url, headers=tts_headers, json=tts_payload)
        audio_path = os.path.join(RESPONSE_FOLDER, "reply.mp3")
        with open(audio_path, "wb") as f:
            f.write(audio_response.content)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    return jsonify({
        "transcription": transcription,
        "message": gpt_reply,
        "mode": mode,
        "audio_url": "/audio/reply.mp3"
    })

@app.route("/audio/reply.mp3")
def get_audio():
    return send_file("responses/reply.mp3", mimetype="audio/mpeg")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050, debug=True)
