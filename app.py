from flask import Flask, request, jsonify
import requests
import os
import re
import lyricsgenius
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
from flask_cors import CORS, cross_origin

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "https://front-end-set-list.vercel.app"}})


CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
genius_token = os.getenv("GENIUS_ACCESS_TOKEN")


@app.route('/', methods=['GET'])
def index():
    return "Servidor em execução! Acesse a API em /api/get_lyrics"


@app.route('/api/get_lyrics', methods=['POST'])
@cross_origin()
def get_lyrics():
    if request.method == 'POST':
        playlist_link = request.json.get('playlist_link')

        try:
            response = requests.get(playlist_link, timeout=10)
            response.raise_for_status()
        except requests.exceptions.Timeout:
            return jsonify({"error": "A solicitação excedeu o tempo limite."}), 500
        except requests.exceptions.HTTPError as e:
            return jsonify({"error": f"Erro ao acessar a playlist: {e}"}), 500

        # Get URI from https link
        if match := re.match(r"https://open.spotify.com/playlist/(.*)\?", playlist_link):
            playlist_uri = match.groups()[0]
        else:
            return jsonify({"error": "Invalid playlist link"}), 400

        # Authenticate with Spotify
        client_credentials_manager = SpotifyClientCredentials(
            client_id=CLIENT_ID, client_secret=CLIENT_SECRET
        )
        session = spotipy.Spotify(
            client_credentials_manager=client_credentials_manager
        )

        # Get list of tracks in the given playlist (note: max playlist length 100)
        tracks = session.playlist_tracks(playlist_uri)["items"]

        genius = lyricsgenius.Genius(genius_token)
        lyrics_list = []

        # Extract name and artist for each track
        for track in tracks:
            name = track["track"]["name"]
            artists = ", ".join(
                [artist["name"] for artist in track["track"]["artists"]]
            )

            # Search for lyrics on Genius
            genius_song = genius.search_song(name, artists)
            if genius_song:
                lyrics_list.append({"name": name, "artists": artists, "lyrics": genius_song.lyrics})
            else:
                lyrics_list.append({"name": name, "artists": artists, "lyrics": "Letra não encontrada"})

        return jsonify({"lyrics": lyrics_list})
    elif request.method == 'GET':
        return "Use o método POST para obter letras. Consulte a documentação para mais detalhes."


if __name__ == '__main__':
    app.run(debug=True)
