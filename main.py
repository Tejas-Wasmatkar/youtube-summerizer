from flask import Flask, render_template, request
from urllib.parse import urlparse, parse_qs
from youtube_transcript_api import (
    YouTubeTranscriptApi,
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable
)
import requests
 
app = Flask(__name__)

def extract_video_id(url):
    """Extract YouTube video ID from a full URL."""
    parsed_url = urlparse(url)
    if parsed_url.hostname == "youtu.be":
        return parsed_url.path[1:]
    elif parsed_url.hostname in ["www.youtube.com", "youtube.com"]:
        return parse_qs(parsed_url.query).get("v", [None])[0]
    return None

def get_transcript(video_id):
    """Fetch the video transcript using YouTube Transcript API."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])
    except TranscriptsDisabled:
        return "Error: Transcripts are disabled for this video."
    except NoTranscriptFound:
        return "Error: No transcript found for this video."
    except VideoUnavailable:
        return "Error: This video is unavailable."
    except Exception as e:
        return f"Error: An unexpected error occurred: {str(e)}"

def summarize_text(transcript):
    """Send the transcript to the local LLaMA 3.3 model via Ollama."""
    prompt = f"Summarize the following YouTube video transcript:\n\n{transcript}"
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "llama3", "prompt": prompt, "stream": False}
        )
        if response.status_code == 200:
            return response.json().get("response", "No summary returned.")
        else:
            return f"Error: Ollama returned a bad response. {response.text}"
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to Ollama. Is the server running?"

@app.route("/", methods=["GET", "POST"])
def index():
    summary = None
    error = None

    if request.method == "POST":
        url = request.form.get("video_url")
        video_id = extract_video_id(url)

        if not video_id:
            error = "Invalid YouTube URL. Please enter a valid video link."
        else:
            transcript = get_transcript(video_id)
            if transcript and not transcript.startswith("Error:"):
                summary = summarize_text(transcript)
                if summary.startswith("Error:"):
                    error = summary
                    summary = None
            else:
                error = transcript  # already contains user-friendly error message

    return render_template("index.html", summary=summary, error=error)

if __name__ == "__main__":
    app.run(debug=True)
