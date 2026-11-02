import streamlit as st
import pandas as pd
import html
import time
import math
import folium
from streamlit_folium import st_folium

try:
    from streamlit_geolocation import streamlit_geolocation
except ImportError:
    streamlit_geolocation = None


# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="ExploreNear | Discover Chennai",
    page_icon="📍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

CSV_FILE = "ExploreNear_Chennai_Final.csv"


# ==================================================
# 2. SESSION STATE
# ==================================================

defaults = {
    "page": "splash",
    "selected_category": "",
    "selected_place": None,
    "splash_seen": False,
    "trip_results": None,
    "trip_start": None,
    "gps_location": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ==================================================
# 3. LOAD DATASET
# ==================================================

@st.cache_data
def load_data():
    data = pd.read_csv(CSV_FILE)
    data.columns = data.columns.str.strip()

    for column in ["Latitude", "Longitude"]:
        if column in data.columns:
            data[column] = pd.to_numeric(
                data[column], errors="coerce"
            )

    return data


try:
    df = load_data()

except Exception as error:
    st.error("Dataset file could not be loaded.")
    st.write(
        "Make sure ExploreNear_Chennai_Final.csv "
        "is in the same folder as app.py."
    )
    st.code(str(error))
    st.stop()


# ==================================================
# 4. CATEGORY INFORMATION
# ==================================================

category_images = {
    "Restaurants & Food":
        "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=800",
    "Religious Places":
        "https://images.unsplash.com/photo-1606293926075-69a00dbfde81?w=800",
    "Tourist & Historical Places":
        "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=800",
    "Shopping Malls":
        "https://images.unsplash.com/photo-1519567241046-7f570eee3ce6?w=800",
    "Parks & Gardens":
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800",
    "Movies & Live Entertainment":
        "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?w=800",
    "Clubs & Nightlife":
        "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=800",
    "Cafes & Coffee Shops":
        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=800",
    "Beaches":
        "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800",
    "Gaming & Entertainment":
        "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=800",
    "Amusement & Water Parks":
        "https://images.unsplash.com/photo-1498307833015-e7b400441eb8?w=800",
    "Sports & Recreation":
        "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=800",
    "Adventure & Outdoor Activities":
        "https://images.unsplash.com/photo-1551632811-561732d1e306?w=800"
}

category_icons = {
    "Restaurants & Food": "🍽️",
    "Religious Places": "🛕",
    "Tourist & Historical Places": "🏛️",
    "Shopping Malls": "🛍️",
    "Parks & Gardens": "🌳",
    "Movies & Live Entertainment": "🎬",
    "Clubs & Nightlife": "🌃",
    "Cafes & Coffee Shops": "☕",
    "Beaches": "🏖️",
    "Gaming & Entertainment": "🎮",
    "Amusement & Water Parks": "🎢",
    "Sports & Recreation": "⚽",
    "Adventure & Outdoor Activities": "🥾"
}

category_descriptions = {
    "Restaurants & Food": "Taste Chennai, one delicious bite at a time.",
    "Religious Places": "Explore peaceful and spiritual destinations.",
    "Tourist & Historical Places": "Discover Chennai's culture and history.",
    "Shopping Malls": "Shop, relax and enjoy your day.",
    "Parks & Gardens": "Take a refreshing break in nature.",
    "Movies & Live Entertainment": "Enjoy movies, shows and live events.",
    "Clubs & Nightlife": "Experience Chennai after sunset.",
    "Cafes & Coffee Shops": "Find your perfect coffee spot.",
    "Beaches": "Enjoy sea views and beautiful sunsets.",
    "Gaming & Entertainment": "Play, compete and have fun.",
    "Amusement & Water Parks": "Make memories with exciting rides.",
    "Sports & Recreation": "Stay active and enjoy sports.",
    "Adventure & Outdoor Activities": "Explore exciting outdoor experiences."
}


# ==================================================
# 5. GENERAL HELPER FUNCTIONS
# ==================================================

def safe(value, default="Not available"):

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    result = str(value).strip()

    if result.lower() in ["", "nan", "none"]:
        return default

    return result


def clean_text(value):
    return html.escape(str(value))


def go_home():
    st.session_state.page = "home"


def show_brand():
    st.markdown(
        '<div class="brand">📍 Explore<span>Near</span></div>',
        unsafe_allow_html=True
    )


def show_header():

    left, right = st.columns([4, 1])

    with left:
        show_brand()

    with right:
        if st.button("⌂ Home", use_container_width=True):
            go_home()
            st.rerun()


def show_detail(label, value, icon):

    st.markdown(
        f"""
<div class="detail-box">
    <div class="detail-label">
        {icon} {clean_text(label)}
    </div>
    <div class="detail-value">
        {clean_text(value)}
    </div>
</div>
""",
        unsafe_allow_html=True
    )


# ==================================================
# 6. TRIP PLANNER FUNCTIONS
# ==================================================

def valid_coordinates(row):

    lat = row.get("Latitude")
    lon = row.get("Longitude")

    if pd.isna(lat) or pd.isna(lon):
        return False

    try:
        lat = float(lat)
        lon = float(lon)

        return (
            8 <= lat <= 14
            and 76 <= lon <= 82
        )

    except (ValueError, TypeError):
        return False


def coordinates_are_verified(row):

    if not valid_coordinates(row):
        return False

    status = safe(
        row.get("Coordinate_Status"), ""
    ).lower()

    # Only use explicitly verified coordinates for GPS distance calculations.
    return (
        status in {
            "verified",
            "verified coordinates",
            "coordinates verified"
        }
    )


def haversine_km(lat1, lon1, lat2, lon2):

    radius = 6371

    lat1 = math.radians(float(lat1))
    lon1 = math.radians(float(lon1))
    lat2 = math.radians(float(lat2))
    lon2 = math.radians(float(lon2))

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * radius * math.asin(math.sqrt(a))


def estimate_visit_minutes(row):

    estimates = {
        "Restaurants & Food": 60,
        "Religious Places": 40,
        "Tourist & Historical Places": 75,
        "Shopping Malls": 90,
        "Parks & Gardens": 45,
        "Movies & Live Entertainment": 150,
        "Clubs & Nightlife": 120,
        "Cafes & Coffee Shops": 45,
        "Beaches": 60,
        "Gaming & Entertainment": 60,
        "Amusement & Water Parks": 180,
        "Sports & Recreation": 60,
        "Adventure & Outdoor Activities": 120
    }

    category = safe(row.get("Category"), "")

    return estimates.get(category, 60)


def estimate_travel_minutes(distance_km):

    return max(
        5,
        math.ceil((distance_km / 20) * 60)
    )


def get_area_places(area):

    if "Area" not in df.columns:
        return df.iloc[0:0].copy()

    return df[
        df["Area"].apply(safe).str.lower()
        == str(area).strip().lower()
    ].copy()


def remove_duplicate_places(data):

    if "Place_ID" in data.columns:
        return data.drop_duplicates(
            subset=["Place_ID"]
        )

    if "Place_Name" in data.columns:
        return data.drop_duplicates(
            subset=["Place_Name"]
        )

    return data.drop_duplicates()


def make_area_trip(area, available_minutes):

    candidates = get_area_places(area)
    candidates = remove_duplicate_places(candidates)

    if candidates.empty:
        return pd.DataFrame(), 0, 0

    selected = []
    total_minutes = 0

    for _, row in candidates.iterrows():

        visit = estimate_visit_minutes(row)

        # Nearby same-area suggestions use a small approximate
        # local travel allowance, not a measured distance.
        travel = 10

        if total_minutes + visit + travel > available_minutes:
            continue

        row = row.copy()

        row["Leg_Distance_km"] = None
        row["Travel_Minutes"] = travel
        row["Visit_Minutes"] = visit
        row["Distance_Available"] = False

        selected.append(row)
        total_minutes += visit + travel

    if not selected:
        return pd.DataFrame(), 0, 0

    result = pd.DataFrame(selected).reset_index(drop=True)

    result.insert(
        0,
        "Visit_Order",
        range(1, len(result) + 1)
    )

    return result, 0, total_minutes


def make_gps_trip(start_lat, start_lon, available_minutes):

    candidates = remove_duplicate_places(df.copy())

    if candidates.empty:
        return pd.DataFrame(), 0, 0

    selected = []
    remaining = candidates.copy()

    current_lat = start_lat
    current_lon = start_lon

    total_minutes = 0
    total_distance = 0

    while not remaining.empty:

        best_index = None
        best_distance = None

        for idx, row in remaining.iterrows():

            visit = estimate_visit_minutes(row)

            if coordinates_are_verified(row):

                distance = haversine_km(
                    current_lat,
                    current_lon,
                    row["Latitude"],
                    row["Longitude"]
                )

                travel = estimate_travel_minutes(distance)

            else:
                # Include places without verified coordinates.
                # Distance cannot honestly be calculated for them.
                distance = None
                travel = 10

            required = visit + travel

            if total_minutes + required <= available_minutes:

                if distance is None:
                    score = 999999
                else:
                    score = distance

                if best_distance is None or score < best_distance:
                    best_distance = score
                    best_index = idx

        if best_index is None:
            break

        row = remaining.loc[best_index].copy()

        if coordinates_are_verified(row):

            distance = haversine_km(
                current_lat,
                current_lon,
                row["Latitude"],
                row["Longitude"]
            )

            travel = estimate_travel_minutes(distance)

            current_lat = float(row["Latitude"])
            current_lon = float(row["Longitude"])

            total_distance += distance

            row["Distance_Available"] = True
            row["Leg_Distance_km"] = round(distance, 2)

        else:

            distance = None
            travel = 10

            row["Distance_Available"] = False
            row["Leg_Distance_km"] = None

        visit = estimate_visit_minutes(row)

        row["Travel_Minutes"] = travel
        row["Visit_Minutes"] = visit

        selected.append(row)

        total_minutes += travel + visit

        remaining = remaining.drop(best_index)

    if not selected:
        return pd.DataFrame(), 0, 0

    result = pd.DataFrame(selected).reset_index(drop=True)

    result.insert(
        0,
        "Visit_Order",
        range(1, len(result) + 1)
    )

    return result, round(total_distance, 2), total_minutes


# ==================================================
# 7. CUSTOM CSS
# ==================================================

st.markdown("""
<style>

.stApp {
    background: #F8F6F0;
    color: #172D4B;
}

#MainMenu, footer, header {
    visibility: hidden;
}

.block-container {
    max-width: 1350px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

.brand {
    font-size: 30px;
    font-weight: 800;
    color: #142C4C;
    margin-bottom: 20px;
    letter-spacing: -1px;
}

.brand span {
    color: #168F83;
}

.hero {
    min-height: 340px;
    border-radius: 25px;
    padding: 50px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    background:
      linear-gradient(90deg,
      rgba(8, 30, 55, 0.94),
      rgba(8, 30, 55, 0.65),
      rgba(8, 30, 55, 0.08)),
      url("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1600");
    background-size: cover;
    background-position: center;
    color: white;
    margin-bottom: 38px;
    box-shadow: 0 12px 30px rgba(20,40,60,0.13);
}

.hero-small {
    color: #9CE0D5;
    letter-spacing: 3px;
    font-size: 12px;
    font-weight: 700;
}

.hero h1 {
    color: white;
    font-family: Georgia, serif;
    font-size: 58px;
    margin: 15px 0;
    line-height: 1.15;
}

.hero h1 span {
    color: #F5D17B;
}

.hero p {
    color: #F1F4F7;
    font-size: 18px;
}

.section-title {
    font-family: Georgia, serif;
    font-size: 34px;
    font-weight: bold;
    color: #142C4C;
    margin-top: 20px;
}

.section-subtitle {
    color: #64748B;
    font-size: 16px;
    margin-bottom: 22px;
}

.category-card {
    background: white;
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid #E8E5DD;
    margin-bottom: 8px;
    box-shadow: 0 5px 15px rgba(20,40,60,0.06);
}

.category-content {
    padding: 14px 15px 17px;
    min-height: 112px;
}

.category-content h3 {
    font-size: 17px;
    color: #172D4B;
    margin: 0 0 9px 0;
}

.category-content p {
    color: #718096;
    font-size: 13px;
    line-height: 1.5;
    margin: 0;
}

.place-card {
    background: white;
    border: 1px solid #E8E5DD;
    padding: 20px;
    border-radius: 17px;
    margin-bottom: 12px;
    box-shadow: 0 4px 14px rgba(20,40,60,0.05);
}

.place-card h3 {
    color: #172D4B;
    font-size: 20px;
    margin-bottom: 7px;
}

.place-card p {
    color: #64748B;
    font-size: 14px;
    line-height: 1.6;
}

.detail-box {
    background: white;
    padding: 20px;
    border-radius: 16px;
    border: 1px solid #E8E5DD;
    margin-bottom: 14px;
    min-height: 90px;
}

.detail-label {
    color: #168F83;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 9px;
}

.detail-value {
    color: #172D4B;
    font-size: 15px;
    line-height: 1.6;
}

.stButton > button {
    background: #168F83;
    color: white;
    border: none;
    border-radius: 11px;
    min-height: 43px;
    font-weight: 600;
}

.stButton > button:hover {
    background: #11776E;
    color: white;
    border: none;
}

.stApp [data-testid="stWidgetLabel"],
.stApp [data-testid="stWidgetLabel"] p,
.stApp [data-testid="stWidgetLabel"] label {
    color: #142C4C !important;
    opacity: 1 !important;
}

.stApp [data-testid="stRadio"] label,
.stApp [data-testid="stRadio"] label p,
.stApp [role="radiogroup"] label,
.stApp [role="radiogroup"] label p {
    color: #142C4C !important;
    opacity: 1 !important;
}

.stApp [data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background-color: #FFFFFF !important;
    border: 1px solid #D8D5CC !important;
    border-radius: 10px !important;
}

.stApp [data-testid="stSelectbox"] [data-baseweb="select"] *,
.stApp [data-testid="stSelectbox"] input {
    color: #142C4C !important;
    -webkit-text-fill-color: #142C4C !important;
}

[data-baseweb="popover"],
[data-baseweb="popover"] [role="option"],
[data-baseweb="menu"] {
    background-color: #FFFFFF !important;
    color: #142C4C !important;
}

[data-baseweb="popover"] [role="option"] * {
    color: #142C4C !important;
}

.stApp input {
    color: #142C4C !important;
    background-color: #FFFFFF !important;
}

.stApp [data-testid="stCaptionContainer"] * {
    color: #64748B !important;
    opacity: 1 !important;
}

.stApp [data-testid="stAlert"] p {
    color: #142C4C !important;
    opacity: 1 !important;
}

.stApp h1,
.stApp h2,
.stApp h3 {
    color: #142C4C;
}

hr {
    border-color: #E8E5DD;
}

</style>
""", unsafe_allow_html=True)


# ==================================================
# 8. SPLASH SCREEN
# ==================================================

if st.session_state.page == "splash":

    st.html("""
<style>
.splash-screen {
    min-height: 78vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    font-family: Arial, sans-serif;
}

.splash-card {
    width: 100%;
    max-width: 1100px;
    min-height: 520px;
    box-sizing: border-box;
    border-radius: 28px;
    padding: 65px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    color: white;
    background:
      linear-gradient(90deg,
      rgba(8,30,55,0.95),
      rgba(8,30,55,0.70),
      rgba(8,30,55,0.12)),
      url("https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=1600");
    background-size: cover;
    background-position: center;
    box-shadow: 0 18px 45px rgba(20,40,60,0.18);
}

.splash-logo {
    color: #9CE0D5;
    font-size: 17px;
    font-weight: bold;
    letter-spacing: 3px;
}

.splash-title {
    font-family: Georgia, serif;
    font-size: clamp(42px, 7vw, 68px);
    font-weight: bold;
    line-height: 1.12;
    margin-top: 55px;
}

.splash-title span {
    color: #F5D17B;
}

.splash-description {
    font-size: 19px;
    color: #F1F4F7;
    margin-top: 22px;
    line-height: 1.7;
}

.splash-tagline {
    margin-top: 48px;
    color: #B7DED8;
    font-size: 12px;
    letter-spacing: 3px;
}

@media(max-width: 600px) {
    .splash-card {
        padding: 30px;
        min-height: 450px;
    }
}
</style>

<div class="splash-screen">
  <div class="splash-card">
    <div class="splash-logo">📍 EXPLORENEAR</div>
    <div class="splash-title">
      Discover<br>
      <span>Chennai.</span>
    </div>
    <div class="splash-description">
      Discover places. Create beautiful memories.
    </div>
    <div class="splash-tagline">
      DISCOVER · EXPLORE · ENJOY
    </div>
  </div>
</div>
""")

    if not st.session_state.splash_seen:
        st.session_state.splash_seen = True
        time.sleep(2)

    st.session_state.page = "home"
    st.rerun()


# ==================================================
# 9. HOME PAGE
# ==================================================

elif st.session_state.page == "home":

    show_header()

    st.markdown("""
<div class="hero">
    <div class="hero-small">YOUR CITY, YOUR EXPERIENCE</div>
    <h1>Explore <span>Chennai</span> ✨</h1>
    <p>Discover places. Create beautiful memories.</p>
</div>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="section-title">Explore by Category</div>
<div class="section-subtitle">
    Pick what you feel like doing today.
</div>
""", unsafe_allow_html=True)

    categories = list(category_images.keys())

    for start in range(0, len(categories), 4):

        row_categories = categories[start:start + 4]
        cols = st.columns(4)

        for col, category in zip(cols, row_categories):

            count = len(
                df[
                    df["Category"].astype(str).str.strip()
                    == category
                ]
            )

            with col:

                st.markdown(
                    '<div class="category-card">',
                    unsafe_allow_html=True
                )

                st.image(
                    category_images[category],
                    use_container_width=True
                )

                st.markdown(
                    f"""
<div class="category-content">
    <h3>{category_icons[category]} {clean_text(category)}</h3>
    <p>{count} places · {clean_text(category_descriptions[category])}</p>
</div>
</div>
""",
                    unsafe_allow_html=True
                )

                if st.button(
                    "Explore category →",
                    key=f"category_{start}_{category}",
                    use_container_width=True
                ):
                    st.session_state.selected_category = category
                    st.session_state.page = "places"
                    st.rerun()

    st.markdown("---")

    st.markdown(
        '<div class="section-title">🧭 Plan Your Trip</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        "Choose your available time and discover nearby places."
    )

    if st.button("Open Trip Planner →", use_container_width=True):
        st.session_state.page = "planner"
        st.session_state.trip_results = None
        st.rerun()

    st.markdown("""
<hr style="margin-top:35px;">
<p style="text-align:center;color:#718096;">
    ExploreNear · Discover Chennai, Your Way
</p>
""", unsafe_allow_html=True)


# ==================================================
# 10. PLACES PAGE
# ==================================================

elif st.session_state.page == "places":

    show_header()

    category = st.session_state.selected_category

    if st.button("← Back to categories"):
        st.session_state.page = "home"
        st.rerun()

    st.markdown(
        f'<div class="section-title">{category_icons.get(category, "📍")} {clean_text(category)}</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="section-subtitle">Find a place for your next experience.</div>',
        unsafe_allow_html=True
    )

    places = df[
        df["Category"].astype(str).str.strip()
        == category
    ].copy()

    if places.empty:

        st.info("No places found in this category.")

    else:

        st.markdown("### Find your perfect place")

        search_col, area_col = st.columns(2)

        with search_col:
            search = st.text_input(
                "🔍 Search places",
                placeholder="Enter a place name...",
                key="place_search"
            )

        with area_col:

            available_areas = sorted([
                area for area in places["Area"].apply(safe).unique()
                if area != "Not available"
            ])

            selected_area = st.selectbox(
                "📍 Select area",
                ["All Areas"] + available_areas,
                key="area_filter"
            )

        if st.button("↻ Clear all filters"):
            st.session_state.place_search = ""
            st.session_state.area_filter = "All Areas"
            st.rerun()

        if search.strip():
            places = places[
                places["Place_Name"].astype(str).str.contains(
                    search.strip(),
                    case=False,
                    na=False
                )
            ]

        if selected_area != "All Areas":
            places = places[
                places["Area"].apply(safe) == selected_area
            ]

        st.markdown(f"**{len(places)} places found**")

        if places.empty:

            st.info("No places match your filters. Try another area.")

        else:

            for index, place in places.iterrows():

                name = safe(place.get("Place_Name"))
                area = safe(place.get("Area"))
                best_for = safe(place.get("Best_For"))
                price = safe(place.get("Entry_Fee_or_Price_Range_INR"))

                st.markdown(
                    f"""
<div class="place-card">
    <h3>{clean_text(name)}</h3>
    <p>📍 {clean_text(area)}</p>
    <p>{clean_text(best_for)}</p>
    <p>🎟️ Entry Fee: {clean_text(price)}</p>
</div>
""",
                    unsafe_allow_html=True
                )

                if st.button("View Details →", key=f"details_{index}"):
                    st.session_state.selected_place = place.to_dict()
                    st.session_state.page = "details"
                    st.rerun()


# ==================================================
# 11. TRIP PLANNER PAGE
# ==================================================

elif st.session_state.page == "planner":

    show_header()

    if st.button("← Back to Home"):
        st.session_state.page = "home"
        st.rerun()

    st.markdown(
        '<div class="section-title">🧭 Plan Your Chennai Trip</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
<div class="section-subtitle">
    Choose your starting point and available time.
    Explore places that fit your schedule.
</div>
""", unsafe_allow_html=True)

    # TIME SELECTION

    st.markdown("### 1. How much time do you have?")

    duration_options = {
        "1 Hour": 60,
        "2 Hours": 120,
        "3 Hours": 180,
        "4 Hours": 240,
        "Full Day (8 Hours)": 480
    }

    duration_choice = st.selectbox(
        "Available trip duration",
        list(duration_options.keys()),
        key="trip_duration"
    )

    available_minutes = duration_options[duration_choice]

    # STARTING LOCATION

    st.markdown("### 2. Select your starting location")

    location_mode = st.radio(
        "Choose how to set your location",
        [
            "Enter area manually",
            "Use my current GPS location"
        ],
        horizontal=True,
        key="location_mode"
    )

    start_location = None
    start_label = ""
    selected_start_area = None

    if location_mode == "Enter area manually":

        areas = sorted([
            area for area in df["Area"].apply(safe).unique()
            if area != "Not available"
        ])

        selected_start_area = st.selectbox(
            "Choose your starting area",
            areas,
            key="starting_area"
        )

        start_label = selected_start_area

        st.success(f"Starting area selected: {selected_start_area}")

    else:

        st.info(
            "Allow location access in your browser when it asks for permission."
        )

        if streamlit_geolocation is None:

            st.error(
                "GPS package is missing. Run "
                "`pip install streamlit-geolocation`."
            )

        else:

            gps_data = streamlit_geolocation()

            if (
                gps_data
                and gps_data.get("latitude") is not None
                and gps_data.get("longitude") is not None
            ):

                start_location = (
                    float(gps_data["latitude"]),
                    float(gps_data["longitude"])
                )

                start_label = "Your current GPS location"

                st.session_state.gps_location = {
                    "lat": start_location[0],
                    "lon": start_location[1]
                }

                st.success("Your current location was received.")

            else:

                st.warning(
                    "GPS location is not available yet. "
                    "Allow browser location permission and try again."
                )

    # GENERATE TRIP

    st.markdown("### 3. Generate your trip")

    if st.button(
        "✨ Find Places for My Trip",
        use_container_width=True
    ):

        with st.spinner("Finding places for your trip..."):

            if location_mode == "Enter area manually":

                trip, distance, total_minutes = make_area_trip(
                    selected_start_area,
                    available_minutes
                )

                trip_start = None

            elif start_location is not None:

                trip, distance, total_minutes = make_gps_trip(
                    start_location[0],
                    start_location[1],
                    available_minutes
                )

                trip_start = start_location

            else:

                trip = pd.DataFrame()
                distance = 0
                total_minutes = 0
                trip_start = None

                st.warning(
                    "Please allow GPS location permission first."
                )

            st.session_state.trip_results = {
                "trip": trip,
                "distance": distance,
                "total_minutes": total_minutes,
                "start": trip_start,
                "start_label": start_label,
                "mode": location_mode
            }

    # DISPLAY RESULTS

    result = st.session_state.trip_results

    if result is not None:

        trip = result["trip"]

        st.markdown("---")
        st.markdown("### ✨ Your Suggested Trip")

        if trip.empty:

            st.info(
                "No places fit this duration. "
                "Please increase your available time."
            )

        else:

            total_visit = int(trip["Visit_Minutes"].sum())
            total_travel = int(trip["Travel_Minutes"].sum())
            total_trip = total_visit + total_travel

            col1, col2, col3, col4 = st.columns(4)

            col1.metric("Places", len(trip))

            if result["mode"] == "Use my current GPS location":
                col2.metric("Known Distance", f'{result["distance"]} km')
            else:
                col2.metric("Starting Area", selected_start_area if selected_start_area else "Selected")

            col3.metric("Estimated Travel Time", f"{total_travel} min")
            col4.metric("Total Duration", f"{total_trip} min")

            st.caption(f"Starting point: {result['start_label']}")

            st.markdown("### 📍 Your Visit Order")

            for _, row in trip.iterrows():

                place_name = clean_text(safe(row.get("Place_Name")))
                area = clean_text(safe(row.get("Area")))
                travel = int(row["Travel_Minutes"])
                visit = int(row["Visit_Minutes"])
                fee = clean_text(
                    safe(row.get("Entry_Fee_or_Price_Range_INR"))
                )

                if row["Distance_Available"] if "Distance_Available" in row else False:

                    distance_text = (
                        f"{row['Leg_Distance_km']} km"
                    )

                else:

                    distance_text = (
                        "Local estimate; exact distance not available"
                    )

                # IMPORTANT:
                # HTML starts at the beginning of the line.
                # This prevents Streamlit from displaying HTML as code.

                card_html = f"""
<div class="place-card">
    <h3>{int(row['Visit_Order'])}. {place_name}</h3>
    <p>📍 {area}</p>
    <p>🚗 Travel from previous point: {distance_text} · {travel} min (approx.)</p>
    <p>⏱️ Suggested visit time: {visit} min</p>
    <p>🎟️ Entry Fee: {fee}</p>
</div>
"""

                st.html(card_html)

            st.caption(
                "Visit durations and travel estimates are approximate. "
                "Actual travel time depends on traffic and route."
            )

            # INTERACTIVE MAP
            # Only places with verified coordinates are shown.

            map_places = trip[
                trip.apply(
                    coordinates_are_verified,
                    axis=1
                )
            ].copy()

            if result["start"] is not None and not map_places.empty:

                st.markdown("### 🗺️ Your Trip Map")

                start_lat, start_lon = result["start"]

                map_object = folium.Map(
                    location=[start_lat, start_lon],
                    zoom_start=12,
                    control_scale=True
                )

                folium.Marker(
                    [start_lat, start_lon],
                    tooltip="Starting Location",
                    popup=result["start_label"],
                    icon=folium.Icon(
                        color="green",
                        icon="home"
                    )
                ).add_to(map_object)

                route_points = [
                    [start_lat, start_lon]
                ]

                for _, row in map_places.iterrows():

                    lat = float(row["Latitude"])
                    lon = float(row["Longitude"])

                    route_points.append([lat, lon])

                    folium.Marker(
                        [lat, lon],
                        tooltip=safe(row.get("Place_Name")),
                        popup=(
                            f"<b>{clean_text(safe(row.get('Place_Name')))}</b>"
                            f"<br>Visit order: {int(row['Visit_Order'])}"
                            f"<br>Area: {clean_text(safe(row.get('Area')))}"
                        ),
                        icon=folium.Icon(
                            color="blue",
                            icon="info-sign"
                        )
                    ).add_to(map_object)

                folium.PolyLine(
                    route_points,
                    color="#168F83",
                    weight=4,
                    opacity=0.8,
                    tooltip="Approximate straight-line route"
                ).add_to(map_object)

                st_folium(
                    map_object,
                    use_container_width=True,
                    height=480,
                    key="explorenear_trip_map"
                )

                st.info(
                    "Map lines show approximate straight-line connections, "
                    "not actual roads. Travel times do not include live traffic."
                )

                last_place = map_places.iloc[-1]

                destination = (
                    f"{last_place['Latitude']},"
                    f"{last_place['Longitude']}"
                )

                google_maps_url = (
                    "https://www.google.com/maps/dir/?api=1"
                    f"&origin={start_lat},{start_lon}"
                    f"&destination={destination}"
                    "&travelmode=driving"
                )

                st.link_button(
                    "Open directions in Google Maps ↗",
                    google_maps_url
                )

            elif result["mode"] == "Enter area manually":

                st.caption(
                    "Your suggestions are based on the selected area. "
                    "A map route needs verified place coordinates."
                )

            else:

                st.caption(
                    "Suggestions are available. A map route will appear "
                    "when verified coordinates are available."
                )


# ==================================================
# 12. PLACE DETAILS PAGE
# ==================================================

elif st.session_state.page == "details":

    show_header()

    place = st.session_state.selected_place

    if place is None:

        st.warning("Please select a place first.")

        if st.button("Go to Home"):
            st.session_state.page = "home"
            st.rerun()

    else:

        if st.button("← Back to places"):
            st.session_state.page = "places"
            st.rerun()

        name = safe(place.get("Place_Name"))
        category = safe(place.get("Category"))

        st.markdown(
            f'<div class="section-title">{clean_text(name)}</div>',
            unsafe_allow_html=True
        )

        st.caption(f"{category} · Chennai")

        photo_url = safe(
            place.get("Official_Photo_URL"),
            ""
        )

        if photo_url.startswith("https://"):

            st.image(
                photo_url,
                use_container_width=True
            )

        elif category in category_images:

            st.image(
                category_images[category],
                use_container_width=True
            )

        st.markdown("### About this place")

        st.write(safe(place.get("Description")))

        col1, col2 = st.columns(2)

        with col1:

            show_detail(
                "Location",
                safe(place.get("Full_Address")),
                "📍"
            )

            show_detail(
                "Opening Time",
                safe(place.get("Opening_Time")),
                "🕒"
            )

            show_detail(
                "Entry Fee / Price",
                safe(place.get("Entry_Fee_or_Price_Range_INR")),
                "🎟️"
            )

            show_detail(
                "Rating",
                safe(place.get("Rating")),
                "⭐"
            )

        with col2:

            show_detail(
                "Closing Time",
                safe(place.get("Closing_Time")),
                "🕔"
            )

            show_detail(
                "Best Time to Visit",
                safe(place.get("Best_Time_to_Visit")),
                "🌇"
            )

            show_detail(
                "Best For",
                safe(place.get("Best_For")),
                "✨"
            )

            show_detail(
                "Reviews",
                safe(place.get("Number_of_Reviews")),
                "💬"
            )

        show_detail(
            "Activities / What is Available",
            safe(place.get("Activities_or_What_is_Available")),
            "🎯"
        )

        show_detail(
            "Facilities",
            safe(place.get("Facilities")),
            "🏢"
        )

        website = safe(
            place.get("Website_or_Source_URL"),
            ""
        )

        if website.startswith("https://") or website.startswith("http://"):
            st.link_button("Visit Website ↗", website)

        st.markdown("""
<hr>
<p style="text-align:center;color:#718096;">
    ExploreNear · Discover Chennai, Your Way
</p>
""", unsafe_allow_html=True)