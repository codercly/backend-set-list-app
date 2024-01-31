from flask import Flask, request, jsonify
import os
import re
import lyricsgenius
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials
from flask_cors import CORS, cross_origin

from concurrent.futures import ThreadPoolExecutor

load_dotenv()

app = Flask(__name__)
app.config['JSONIFY_TIMEOUT'] = 60
CORS(app, resources={r"/api/*": {"origins": "https://front-end-set-list.vercel.app"}}, support_credentials=True)

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
genius_token = os.getenv("GENIUS_ACCESS_TOKEN")

executor = ThreadPoolExecutor()

lyrics_cache = {}


def get_spotify_session():
    client_credentials_manager = SpotifyClientCredentials(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )
    return spotipy.Spotify(client_credentials_manager=client_credentials_manager)


def get_playlist_uri(playlist_link):
    match = re.match(r"https://open.spotify.com/playlist/(.*)\?", playlist_link)
    return match.groups()[0] if match else None


def get_genius_lyrics(name, artists):
    genius = lyricsgenius.Genius(genius_token, timeout=15)
    genius_song = genius.search_song(name, artists)
    return genius_song.lyrics if genius_song else "Letra não encontrada"


def process_track(track):
    name = track["track"]["name"]
    artists = ", ".join([artist["name"] for artist in track["track"]["artists"]])

    cache_key = f"{name}_{artists}"
    if cache_key in lyrics_cache:
        lyrics = lyrics_cache[cache_key]
    else:
        lyrics = get_genius_lyrics(name, artists)
        lyrics_cache[cache_key] = lyrics

    return {"name": name, "artists": artists, "lyrics": lyrics}


@app.route('/', methods=['GET'])
def index():
    return "Servidor em execução! Acesse a API em /api/get_lyrics"


@app.route('/api/get_lyrics', methods=['POST', 'GET'])
@cross_origin(supports_credentials=True)
def get_lyrics():
    if request.method == 'POST':
        playlist_link = request.json.get('playlist_link')
        session = get_spotify_session()

        playlist_uri = get_playlist_uri(playlist_link)
        if not playlist_uri:
            return jsonify({"error": "link da playlist inválido"}), 400

        tracks = session.playlist_tracks(playlist_uri)["items"]

        page_size = 5
        total_tracks = len(tracks)
        num_pages = (total_tracks + page_size - 1) // page_size

        lyrics_list = []

        for page in range(num_pages):
            start_index = page * page_size
            end_index = (page + 1) * page_size
            current_tracks = tracks[start_index:end_index]

            futures = [executor.submit(process_track, track) for track in current_tracks]
            lyrics_list.extend([future.result() for future in futures])

        return jsonify({"lyrics":lyrics_list})

    elif request.method == 'GET':
        return "Use o método POST para obter as letras"


if __name__ == '__main__':
    app.run(debug=True)
