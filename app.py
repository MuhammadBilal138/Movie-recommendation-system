import requests
import streamlit as st
import warnings

# =============================
# CONFIG
# =============================
API_BASE = "https://movie-rec-466x.onrender.com" or "http://127.0.0.1:8000"
TMDB_IMG = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="Movie Recommendation System", page_icon="", layout="wide")

# Silence deprecation warnings completely (extra safety)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# =============================
# STYLES
# =============================
st.markdown(
    """
<style>
.block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1400px; }
.small-muted { color:#6b7280; font-size: 0.92rem; }
.movie-title { font-size: 0.9rem; line-height: 1.15rem; height: 2.3rem; overflow: hidden; }
.card { border: 1px solid rgba(0,0,0,0.08); border-radius: 16px; padding: 14px; background: rgba(255,255,255,0.7); }
</style>
""",
    unsafe_allow_html=True,
)

# =============================
# STATE
# =============================
if "view" not in st.session_state:
    st.session_state.view = "home"
if "selected_tmdb_id" not in st.session_state:
    st.session_state.selected_tmdb_id = None

qp_view = st.query_params.get("view")
qp_id = st.query_params.get("id")
if qp_view in ("home", "details"):
    st.session_state.view = qp_view
if qp_id:
    try:
        st.session_state.selected_tmdb_id = int(qp_id)
        st.session_state.view = "details"
    except:
        pass


def goto_home():
    st.session_state.view = "home"
    st.query_params.clear()
    st.query_params["view"] = "home"
    st.rerun()


def goto_details(tmdb_id: int):
    st.session_state.view = "details"
    st.session_state.selected_tmdb_id = int(tmdb_id)
    st.query_params["view"] = "details"
    st.query_params["id"] = str(tmdb_id)
    st.rerun()


# =============================
# API HELPERS
# =============================
@st.cache_data(ttl=30)
def api_get_json(path: str, params: dict | None = None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=25)
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}: {r.text[:300]}"
        return r.json(), None
    except Exception as e:
        return None, f"Request failed: {e}"


def poster_grid(cards, cols=6, key_prefix="grid"):
    if not cards:
        st.info("No movies to show.")
        return

    rows = (len(cards) + cols - 1) // cols
    idx = 0
    for r in range(rows):
        colset = st.columns(cols)
        for c in range(cols):
            if idx >= len(cards):
                break
            m = cards[idx]
            idx += 1

            with colset[c]:
                if m.get("poster_url"):
                    st.image(m["poster_url"], use_container_width=True)
                else:
                    st.write("No poster")

                if st.button("Open", key=f"{key_prefix}_{r}_{c}_{idx}"):
                    goto_details(m["tmdb_id"])

                st.markdown(
                    f"<div class='movie-title'>{m.get('title','')}</div>",
                    unsafe_allow_html=True,
                )


def to_cards_from_tfidf_items(items):
    cards = []
    for x in items or []:
        tmdb = x.get("tmdb") or {}
        if tmdb.get("tmdb_id"):
            cards.append(
                {
                    "tmdb_id": tmdb["tmdb_id"],
                    "title": tmdb.get("title") or "Untitled",
                    "poster_url": tmdb.get("poster_url"),
                }
            )
    return cards


# =============================
# SIDEBAR
# =============================
with st.sidebar:
    st.markdown("Menu")
    if st.button("Home"):
        goto_home()

    st.markdown("---")
    home_category = st.selectbox(
        "Category",
        ["trending", "popular", "top_rated", "now_playing", "upcoming"],
    )
    grid_cols = st.slider("Grid columns", 4, 8, 6)


# =============================
# HEADER
# =============================
st.title("Movie Recommendation System")
st.markdown(
    "<div class='small-muted'>Search → open details → get recommendations</div>",
    unsafe_allow_html=True,
)
st.divider()

# =============================
# HOME
# =============================
if st.session_state.view == "home":
    typed = st.text_input("Search movie")

    if typed.strip():
        data, err = api_get_json("/tmdb/search", params={"query": typed})
        if err:
            st.error(err)
        else:
            poster_grid(data, cols=grid_cols, key_prefix="search")
        st.stop()

    home_cards, err = api_get_json(
        "/home", params={"category": home_category, "limit": 24}
    )
    if err:
        st.error(err)
    else:
        poster_grid(home_cards, cols=grid_cols, key_prefix="home")

# =============================
# DETAILS
# =============================
elif st.session_state.view == "details":
    tmdb_id = st.session_state.selected_tmdb_id
    data, err = api_get_json(f"/movie/id/{tmdb_id}")

    if err or not data:
        st.error("Failed to load movie details")
        st.stop()

    left, right = st.columns([1, 2.5], gap="large")

    with left:
        st.image(data["poster_url"], use_container_width=True)

    with right:
        st.markdown(f"## {data.get('title','')}")
        st.write(data.get("overview", ""))

    st.divider()
    st.markdown("### Recommendations")

    bundle, _ = api_get_json("/movie/search", params={"query": data["title"]})
    poster_grid(
        to_cards_from_tfidf_items(bundle.get("tfidf_recommendations")),
        cols=grid_cols,
        key_prefix="rec",
    )
