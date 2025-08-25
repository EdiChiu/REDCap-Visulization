import pandas as pd
import pydeck as pdk
import streamlit as st

# Load CSVs
institutions_df = pd.read_csv("Institutions.csv")
coordinates_df = pd.read_csv("Institution_Coordinates.csv")

# Dynamically find the correct column for "Current Institution"
col_name = [col for col in institutions_df.columns if 'Current Institution' in col][0]

# Count how many people are at each institution
institution_counts = institutions_df[col_name].value_counts().reset_index()
institution_counts.columns = ['Institution', 'Count']

# Merge institution counts with coordinates
merged_df = pd.merge(institution_counts, coordinates_df, how='left', on='Institution')

# Drop rows without coordinates
filtered_df = merged_df.dropna(subset=['Latitude', 'Longitude'])

# Rename columns for pydeck
map_data = filtered_df.rename(columns={'Latitude': 'lat', 'Longitude': 'lon'})

# Streamlit UI
st.title("CAIRIBU Institution Map")
st.map(map_data[['lat', 'lon']])

# Show interactive map with proportional circles
st.pydeck_chart(pdk.Deck(
    initial_view_state=pdk.ViewState(
        latitude=map_data['lat'].mean(),
        longitude=map_data['lon'].mean(),
        zoom=1,
        pitch=0,
    ),
    layers=[
        pdk.Layer(
            'ScatterplotLayer',
            data=map_data,
            get_position='[lon, lat]',
            get_radius='20000 + Count * 500',
            get_fill_color='[0, 128, 255, 180]',
            pickable=True,
            auto_highlight=True,
        ),
    ],
    tooltip={"text": "{Institution}\nCount: {Count}"}
))

# Optional: Display the data table below the map
st.subheader("Institution Counts with Coordinates")
st.dataframe(map_data)

# Detect a country column (case-insensitive)
country_col = next((c for c in map_data.columns if 'country' in c.lower()), None)

if country_col is None:
    # Try to infer country from coordinates using reverse_geocoder (offline) for best results.
    try:
        import reverse_geocoder as rg
        import pycountry

        # Prepare coords as (lat, lon) tuples for rg.search
        coords = list(zip(map_data['lat'].astype(float).tolist(), map_data['lon'].astype(float).tolist()))
        rg_results = rg.search(coords)  # list of dicts with 'cc' (country code) and 'name'

        countries = []
        for res in rg_results:
            cc = res.get('cc')
            try:
                # Map alpha-2 code to full country name
                country = pycountry.countries.get(alpha_2=cc).name
            except Exception:
                country = res.get('name', '')
            countries.append(country)

        map_data['Country'] = countries
        country_col = 'Country'
    except Exception:
        # Fallback: bounding-box heuristics to determine if a coordinate is within US territories
        def infer_country_from_bbox(lat, lon):
            try:
                lat = float(lat); lon = float(lon)
            except Exception:
                return ''
            # Contiguous US
            if 24.0 <= lat <= 50.0 and -125.0 <= lon <= -66.0:
                return 'United States'
            # Alaska
            if 50.0 <= lat <= 72.0 and -170.0 <= lon <= -129.0:
                return 'United States'
            # Hawaii
            if 18.0 <= lat <= 23.0 and -161.0 <= lon <= -154.0:
                return 'United States'
            # Puerto Rico
            if 17.0 <= lat <= 19.0 and -68.0 <= lon <= -65.0:
                return 'United States'
            return 'Non-US'

        map_data['Country'] = map_data.apply(lambda r: infer_country_from_bbox(r['lat'], r['lon']), axis=1)
        country_col = 'Country'

# Ensure Count is numeric
map_data['Count'] = pd.to_numeric(map_data['Count'], errors='coerce').fillna(0).astype(int)

# Clean country values
map_data['country_clean'] = map_data[country_col].astype(str).str.strip()

# Common variants for United States
us_variants = {'united states', 'united states of america', 'usa', 'us', 'u.s.', 'u.s.a.'}

# Mask for non-US rows (ignore empty/null country names)
non_us_mask = ~map_data['country_clean'].str.lower().isin(us_variants) & (map_data['country_clean'].str.strip() != '')

non_us_df = map_data[non_us_mask].copy()

# Totals
total_people_outside_us = int(non_us_df['Count'].sum())
unique_institutions_outside_us = int(non_us_df['Institution'].nunique())

st.subheader("International (outside US) Summary")
st.write(f"Total CAIRIBU community members outside the US: {total_people_outside_us}")
st.write(f"Unique institutions outside the US: {unique_institutions_outside_us}")

if non_us_df.empty:
    st.info("No non-US institutions found (based on the detected/inferred country column).")
else:
    # Show the actual rows flagged as non-US (similar to st.dataframe(map_data))
    display_cols = [c for c in ['Institution', 'Count', 'lat', 'lon', country_col] if c in non_us_df.columns]
    st.subheader("International rows (non-US institutions)")
    st.dataframe(non_us_df[display_cols].reset_index(drop=True))
