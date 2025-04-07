# backend/api/voice.py

import os
import requests
from flask import Blueprint, request, jsonify, Response
from dotenv import load_dotenv

load_dotenv()
voice_bp = Blueprint("voice", __name__)

@voice_bp.route("/speak", methods=["POST"])
def speak():
    data = request.json
    text = data.get("text", "")
    voice_id = data.get("voice_id", "cgSgspJ2msm6clMCkdW9")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return jsonify({"error": "Missing ElevenLabs API key"}), 500

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return Response(response.content, content_type="audio/mpeg")
    else:
        print("ElevenLabs Error:", response.status_code, response.text)
        return jsonify({"error": "Failed to generate audio"}), 500
