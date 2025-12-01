import streamlit as st
import pickle
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ------------------------------
# Page Configuration
# ------------------------------
st.set_page_config(
    page_title="Movie Magic Recommender",
    page_icon="🍿",
    layout="wide"
)

# ------------------------------
# Session State Initialization
# ------------------------------
if "history" not in st.session_state:
    st.session_state.history = []
if "mode" not in st.session_state:
    st.session_state.mode = None
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None
if "random_movie" not in st.session_state:
    st.session_state.random_movie = None

# ------------------------------
# TMDB API KEY
# ------------------------------
TMDB_API_KEY = st.secrets["tmdb"]["api_key"]

# ------------------------------
# Retry Session Function
# ------------------------------
def requests_retry_session(
    retries=5,
    backoff_factor=1,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# ------------------------------
# Safe Image Loader
# ------------------------------
def safe_image(url):
    return url if url else "https://i.ibb.co/ZVFsg37/no-image-icon.png"


# ------------------------------
# API Functions
# ------------------------------
def fetch_poster(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}"
        response = requests_retry_session().get(url)
        if response.status_code == 200:
            data = response.json()
            poster_path = data.get("poster_path")
            if poster_path:
                return f"https://image.tmdb.org/t/p/w500{poster_path}"
    except:
        pass
    return None


def fetch_trailer(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API_KEY}"
        response = requests_retry_session().get(url)
        if response.status_code == 200:
            for video in response.json().get("results", []):
                if video.get("type") == "Trailer" and video.get("site") == "YouTube":
                    return f"https://youtu.be/{video['key']}"
    except:
        pass
    return None


def get_movie_details(movie_id):
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,videos"
        response = requests_retry_session().get(url)

        if response.status_code == 200:
            data = response.json()
            directors = [
                crew["name"] for crew in data.get("credits", {}).get("crew", [])
                if crew.get("job") == "Director"
            ]

            cast = data.get("credits", {}).get("cast", [])[:5]
            cast_details = [{
                "name": c.get("name"),
                "character": c.get("character"),
                "profile": f"https://image.tmdb.org/t/p/w500{c['profile_path']}" if c.get("profile_path") else None
            } for c in cast]

            genres = ", ".join([g["name"] for g in data.get("genres", [])])
            budget = f"${data.get('budget', 0):,}" if data.get("budget", 0) > 0 else "N/A"
            revenue = f"${data.get('revenue', 0):,}" if data.get("revenue", 0) > 0 else "N/A"
            available_in = ", ".join([lang["english_name"] for lang in data.get("spoken_languages", [])])

            return {
                "rating": data.get("vote_average"),
                "vote_count": data.get("vote_count"),
                "release_date": data.get("release_date"),
                "runtime": data.get("runtime"),
                "tagline": data.get("tagline"),
                "overview": data.get("overview"),
                "director": ", ".join(directors),
                "cast": cast_details,
                "genres": genres,
                "budget": budget,
                "revenue": revenue,
                "available_in": available_in,
            }
    except:
        pass

    return None


# ------------------------------
# Recommendation System
# ------------------------------
def recommend(movie):
    index = movies[movies["title"] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    recommendations = []

    for i in distances[1:6]:
        rec_movie_id = movies.iloc[i[0]].movie_id
        poster = fetch_poster(rec_movie_id)

        recommendations.append({
            "title": movies.iloc[i[0]].title,
            "poster": poster,
            "trailer": fetch_trailer(rec_movie_id)
        })

    return recommendations


def get_random_movie():
    random_movie = movies.sample(1).iloc[0]
    return {
        "title": random_movie["title"],
        "poster": fetch_poster(random_movie["movie_id"]),
        "trailer": fetch_trailer(random_movie["movie_id"]),
        "movie_id": random_movie["movie_id"]
    }


def update_history(movie_id):
    if not st.session_state.history or st.session_state.history[-1] != movie_id:
        st.session_state.history.append(movie_id)
        if len(st.session_state.history) > 5:
            st.session_state.history.pop(0)


def get_trending_movies():
    try:
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}"
        response = requests_retry_session().get(url)

        if response.status_code == 200:
            data = response.json()
            trending_list = []

            for movie in data.get("results", [])[:5]:
                trending_list.append({
                    "title": movie.get("title"),
                    "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else None,
                    "movie_id": movie.get("id")
                })
            return trending_list
    except:
        pass

    return []


# ------------------------------
# Load Data
# ------------------------------
movies = pickle.load(open("model_files/movie_list.pkl", "rb"))
similarity = pickle.load(open("model_files/similarity.pkl", "rb"))

# ------------------------------
# HEADER
# ------------------------------
st.markdown("""
<h1 style='text-align:center;color:#FF4B4B;'>Let’s Find the Perfect Movie for You! 🎬✨</h1>
<p style='text-align:center;color:#7f8c8d;font-size:1.3rem;'>Pick a movie or get a surprise recommendation!</p>
""", unsafe_allow_html=True)

st.markdown("---")

# ------------------------------
# TRENDING MOVIES
# ------------------------------
st.markdown("<h2 style='text-align:center;color:#FF4B4B;'>🔥 Trending Movies</h2>", unsafe_allow_html=True)

trending_movies = get_trending_movies()
cols = st.columns(5)

for idx, movie in enumerate(trending_movies):
    with cols[idx]:
        st.image(safe_image(movie["poster"]), use_column_width=True)
        st.markdown(f"<p style='text-align:center;'>{movie['title']}</p>", unsafe_allow_html=True)

st.markdown("---")


# ------------------------------
# SEARCH & SURPRISE
# ------------------------------
col_left, col_mid, col_right = st.columns([3, 1, 2])

with col_left:
    st.subheader("🔍 Search for a Movie")
    selected_movie = st.selectbox("Search here...", movies["title"].values)

    if st.button("Show Details & Recommendations"):
        st.session_state.mode = "search"
        st.session_state.selected_movie = selected_movie
        st.balloons()

with col_right:
    st.subheader("🎭 Surprise Me!")
    if st.button("Random Movie 🎲"):
        st.session_state.mode = "surprise"
        st.session_state.random_movie = get_random_movie()
        st.balloons()


# ------------------------------
# MOVIE DETAILS SECTION
# ------------------------------
if st.session_state.mode:

    if st.session_state.mode == "search":
        movie_title = st.session_state.selected_movie
        movie_row = movies[movies["title"] == movie_title].iloc[0]
        movie_id = movie_row.movie_id

    else:
        movie_data = st.session_state.random_movie
        movie_title = movie_data["title"]
        movie_id = movie_data["movie_id"]

    update_history(movie_id)
    details = get_movie_details(movie_id)
    trailer_url = fetch_trailer(movie_id)

    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown(f"<h2>🎬 {movie_title}</h2>", unsafe_allow_html=True)

    left, right = st.columns([1, 2])

    with left:
        st.image(safe_image(fetch_poster(movie_id)), use_column_width=True)

    with right:
        if details:
            st.markdown("### ⭐ Ratings & Runtime")
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Rating:** {details['rating']} / 10")
            c2.write(f"**Votes:** {details['vote_count']}")
            c3.write(f"**Runtime:** {details['runtime']} mins")

            if details.get("tagline"):
                st.info(details["tagline"])

            st.markdown("### 📘 Overview")
            st.write(details["overview"])

            st.markdown("### 🎬 Production")
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Release Date:** {details['release_date']}")
            c2.write(f"**Budget:** {details['budget']}")
            c3.write(f"**Revenue:** {details['revenue']}")

            st.markdown("### 🎭 Cast")
            cast_cols = st.columns(len(details["cast"]))
            for idx, actor in enumerate(details["cast"]):
                with cast_cols[idx]:
                    st.image(safe_image(actor["profile"]), use_column_width=True)
                    st.caption(f"{actor['name']} as {actor['character']}")

    if trailer_url:
        with st.expander("🎞 Watch Trailer"):
            st.video(trailer_url)


    # ------------------------------
    # RECOMMENDATIONS
    # ------------------------------
    st.markdown("<hr>", unsafe_allow_html=True)
    st.subheader("🚀 Recommended Movies")

    recommendations = recommend(movie_title)
    rec_cols = st.columns(3)

    for idx, rec in enumerate(recommendations):
        with rec_cols[idx % 3]:
            st.image(safe_image(rec["poster"]), use_column_width=True)
            st.markdown(f"<p style='text-align:center;'><b>{rec['title']}</b></p>", unsafe_allow_html=True)
            if rec["trailer"]:
                with st.expander("Trailer"):
                    st.video(rec["trailer"])


# ------------------------------
# SIDEBAR HISTORY
# ------------------------------
with st.sidebar:
    st.header("🕒 Recently Viewed")

    if st.session_state.history:
        for hist_id in reversed(st.session_state.history):
            movie_row = movies[movies["movie_id"] == hist_id].iloc[0]
            title = movie_row["title"]
            poster = fetch_poster(hist_id)

            st.image(safe_image(poster), width=100)

            if st.button(title, key=f"hist_{hist_id}"):
                st.session_state.mode = "search"
                st.session_state.selected_movie = title
                st.experimental_rerun()
    else:
        st.write("No history yet.")


# ------------------------------
# FOOTER
# ------------------------------
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center;color:#888;'>Made with ❤️ by <b>Dhammadeep Tuljapure</b></p>", unsafe_allow_html=True)
