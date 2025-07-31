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
            get_radius='20000 + Count * 100',
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
