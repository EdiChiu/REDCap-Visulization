import streamlit as st
import pandas as pd
import time
import pydeck as pdk
from geopy.geocoders import ArcGIS, Nominatim

@st.cache_data
def load_data(uploaded_file):
    # read the true header row (row 0), only 3 data rows
    df = pd.read_excel(uploaded_file, header=0)
    df.columns = [str(c).strip() for c in df.columns]
    return df

@st.cache_data
def geocode_addresses(addresses):
    arc = ArcGIS(timeout=10)
    nom = Nominatim(user_agent="cairibu_address_mapper", timeout=10)
    coords = {}
    for addr in addresses:
        if not addr or pd.isna(addr):
            coords[addr] = (None, None)
            continue

        # try ArcGIS first
        loc = None
        try:
            loc = arc.geocode(addr)
        except Exception:
            pass

        # fallback to Nominatim if ArcGIS failed
        if not loc:
            try:
                loc = nom.geocode(addr)
            except Exception:
                pass

        coords[addr] = (loc.latitude, loc.longitude) if loc else (None, None)
        time.sleep(0.5)   # still polite, but faster
    return coords

st.title("CAIRIBU Institutions Map (by Mailing Address)")

uploaded_file = st.file_uploader("Upload CAIRIBU outreach .xlsx", type="xlsx")
if not uploaded_file:
    st.info("Please upload your outreach spreadsheet.")
    st.stop()

df = load_data(uploaded_file)

# collapse and normalize headers for matching
normalized = {orig: " ".join(orig.lower().split()) for orig in df.columns}

# 1) find your “Current Institution” column
inst_cols = [o for o,n in normalized.items() if n.startswith("current institution")]
if not inst_cols:
    st.error("Couldn’t find “Current Institution” header.\n\nAvailable:\n• " + "\n• ".join(df.columns))
    st.stop()
inst_col = inst_cols[0]

# 2) find your “Institutional Mailing Address” column
addr_cols = [o for o,n in normalized.items() if "institutional mailing address" in n]
if not addr_cols:
    st.error("Couldn’t find “Institutional Mailing Address” header.\n\nAvailable:\n• " + "\n• ".join(df.columns))
    st.stop()
addr_col = addr_cols[0]

# 3) prepare
df["institution"] = df[inst_col].astype(str).str.strip()
df["address"]     = df[addr_col].astype(str).str.strip()

# 4) geocode
unique_addrs = df["address"].dropna().unique()
coords = geocode_addresses(unique_addrs)

# show you exactly what came back
st.subheader("Raw geocode results")
st.write(pd.DataFrame.from_dict(coords, orient="index", columns=["lat","lon"]))

# 5) map coords back onto rows
df["lat"] = df["address"].map(lambda a: coords.get(a,(None,None))[0])
df["lon"] = df["address"].map(lambda a: coords.get(a,(None,None))[1])

# 6) filter & aggregate
df_valid = df.dropna(subset=["lat","lon"])
if df_valid.empty:
    st.error("Still no valid geocoded addresses.  Check your raw results above.")
    st.stop()

agg = (
    df_valid
      .groupby(["institution","lat","lon"])
      .size()
      .reset_index(name="count")
)

# 7) render map
view = pdk.ViewState(
    latitude=agg["lat"].mean(),
    longitude=agg["lon"].mean(),
    zoom=3
)
layer = pdk.Layer(
    "ScatterplotLayer",
    data=agg,
    get_position='[lon, lat]',
    get_radius='count * 30000',
    get_fill_color='[0, 128, 255, 180]',
    pickable=True,
    auto_highlight=True
)
deck = pdk.Deck(
    layers=[layer],
    initial_view_state=view,
    tooltip={"text":"Institution: {institution}\nCount: {count}"}
)
st.pydeck_chart(deck)

st.subheader("Counts by Institution")
st.dataframe(agg.set_index("institution"))
