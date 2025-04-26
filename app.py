import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import folium_static
import folium
import numpy as np
from datetime import datetime

# Page configuration for better layout
st.set_page_config(layout="wide")

@st.cache_data
def load_data(path):
    return pd.read_csv(path)

# Load and preprocess data
df = load_data("data/portsmouth_housing_data.csv")
df.fillna(0, inplace=True)  # Replace NaN with 0 for numeric calculations

# Define housing goals
RENTAL_GOAL = 2700
OWNER_GOAL = 220
TOTAL_GOAL = RENTAL_GOAL + OWNER_GOAL
TARGET_YEAR = 2030
CURRENT_YEAR = datetime.now().year

st.title("Portsmouth Housing Dashboard")
st.subheader(f"Progress towards 2030 Housing Goals")

# Create columns with consistent unit counts
df["Rental Units"] = df["Market Rate Rentals"] + df["Affordable Rentals"]
df["Owner Units"] = df["Market Rate Owner"] + df["Affordable Owner"]

# Convert move-in date to year and ensure it's numeric
df["Move-in Year"] = pd.to_numeric(df["Move-in date"], errors='coerce')

# Filter out rows with invalid years
df_valid = df[~pd.isna(df["Move-in Year"])].copy()

# Group by year
yearly_data = df_valid.groupby("Move-in Year").agg({
    "Rental Units": "sum",
    "Owner Units": "sum",
    "Total units": "sum"
}).reset_index()

# Create year range from earliest year to 2030
all_years = list(range(int(yearly_data["Move-in Year"].min()), TARGET_YEAR + 1))
complete_years = pd.DataFrame({"Move-in Year": all_years})

# Merge with actual data
yearly_complete = complete_years.merge(yearly_data, on="Move-in Year", how="left").fillna(0)

# Calculate cumulative sums
yearly_complete["Cumulative Rental"] = yearly_complete["Rental Units"].cumsum()
yearly_complete["Cumulative Owner"] = yearly_complete["Owner Units"].cumsum()
yearly_complete["Cumulative Total"] = yearly_complete["Total units"].cumsum()

# Show current progress metrics
current_rental = yearly_complete["Cumulative Rental"].iloc[-1] if not yearly_complete.empty else 0
current_owner = yearly_complete["Cumulative Owner"].iloc[-1] if not yearly_complete.empty else 0

# Calculate deficits
rental_deficit = RENTAL_GOAL - current_rental
owner_deficit = OWNER_GOAL - current_owner
total_deficit = TOTAL_GOAL - (current_rental + current_owner)

# Progress metrics in a row - Placed rental deficit next to rental progress
col1, col2, col3, col4 = st.columns(4)
with col1:
    rental_progress = (current_rental / RENTAL_GOAL) * 100
    st.metric("Rental Units Progress", f"{int(current_rental)} / {RENTAL_GOAL}", f"{rental_progress:.1f}%")

with col2:
    st.metric("Rental Units Deficit", f"{int(rental_deficit)}", 
              f"Need {int(rental_deficit)} more units by 2030", delta_color="inverse")

with col3:
    owner_progress = (current_owner / OWNER_GOAL) * 100
    st.metric("Owner Units Progress", f"{int(current_owner)} / {OWNER_GOAL}", f"{owner_progress:.1f}%")

with col4:
    total_progress = ((current_rental + current_owner) / TOTAL_GOAL) * 100
    st.metric("Total Units Progress", f"{int(current_rental + current_owner)} / {TOTAL_GOAL}", f"{total_progress:.1f}%")

# Create two-column layout for the charts
left_col, right_col = st.columns([1, 1])

# LEFT COLUMN CONTENT - RENTAL UNITS CHART
# ─────────────────────────────────────────────────────────
with left_col:
    # 1) RENTAL UNITS CHART
    st.subheader(f"Rental Housing Progress")

    # Create rental progress chart
    rental_fig = go.Figure()

    # Bar chart for annual rental units
    rental_fig.add_trace(go.Bar(
        x=yearly_data["Move-in Year"],
        y=yearly_data["Rental Units"],
        name="New Rental Units",
        marker_color="royalblue",
        opacity=0.7
    ))

    # Line for cumulative rental progress
    rental_fig.add_trace(go.Scatter(
        x=yearly_complete["Move-in Year"],
        y=yearly_complete["Cumulative Rental"],
        mode="lines+markers",
        name="Cumulative Rental Units",
        line=dict(color="blue", width=3)
    ))

    # Add rental goal line
    rental_fig.add_trace(go.Scatter(
        x=[yearly_complete["Move-in Year"].min(), TARGET_YEAR],
        y=[0, RENTAL_GOAL],
        mode="lines",
        name="2030 Rental Goal",
        line=dict(color="navy", width=2, dash="dash")
    ))

    # Calculate and add projected rental trendline
    if len(yearly_data) >= 2:
        rental_years = yearly_data["Move-in Year"].values
        rental_cum = yearly_data["Rental Units"].cumsum().values
        
        # Calculate linear trend
        rental_coef = np.polyfit(rental_years, rental_cum, 1)
        rental_poly1d = np.poly1d(rental_coef)
        
        # Project to 2030
        proj_years = np.array(range(int(yearly_data["Move-in Year"].max()) + 1, TARGET_YEAR + 1))
        
        if len(proj_years) > 0:
            rental_projections = rental_poly1d(proj_years)
            
            # Add projected line
            rental_fig.add_trace(go.Scatter(
                x=proj_years,
                y=rental_projections,
                mode="lines",
                name="Projected Rental Trend",
                line=dict(color="lightblue", width=3, dash="dot")
            ))
            
            # Calculate and display projected deficit
            projected_rental_by_2030 = rental_poly1d(TARGET_YEAR)
            projected_rental_deficit = max(0, RENTAL_GOAL - projected_rental_by_2030)
            
            if projected_rental_deficit > 0:
                rental_fig.add_annotation(
                    x=TARGET_YEAR,
                    y=projected_rental_by_2030,
                    text=f"Projected deficit: {int(projected_rental_deficit)} units",
                    showarrow=True,
                    arrowhead=1,
                    ax=50,
                    ay=-40,
                    font=dict(size=12, color="red"),
                    bordercolor="red",
                    bgcolor="white"
                )

    # Update rental chart layout
    rental_fig.update_layout(
        title="Rental Units Progress Toward 2030 Goal (2,700 Units)",
        xaxis_title="Year",
        yaxis_title="Rental Units",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450
    )

    st.plotly_chart(rental_fig, use_container_width=True)

# RIGHT COLUMN CONTENT - OWNER UNITS CHART
# ─────────────────────────────────────────────────────────
with right_col:
    # 2) OWNER UNITS CHART
    st.subheader(f"Owner Housing Progress")

    # Create owner progress chart
    owner_fig = go.Figure()

    # Bar chart for annual owner units
    owner_fig.add_trace(go.Bar(
        x=yearly_data["Move-in Year"],
        y=yearly_data["Owner Units"],
        name="New Owner Units",
        marker_color="green",
        opacity=0.7
    ))

    # Line for cumulative owner progress
    owner_fig.add_trace(go.Scatter(
        x=yearly_complete["Move-in Year"],
        y=yearly_complete["Cumulative Owner"],
        mode="lines+markers",
        name="Cumulative Owner Units",
        line=dict(color="darkgreen", width=3)
    ))

    # Add owner goal line
    owner_fig.add_trace(go.Scatter(
        x=[yearly_complete["Move-in Year"].min(), TARGET_YEAR],
        y=[0, OWNER_GOAL],
        mode="lines",
        name="2030 Owner Goal",
        line=dict(color="green", width=2, dash="dash")
    ))

    # Calculate and add projected owner trendline
    if len(yearly_data) >= 2:
        owner_years = yearly_data["Move-in Year"].values
        owner_cum = yearly_data["Owner Units"].cumsum().values
        
        # Calculate linear trend
        owner_coef = np.polyfit(owner_years, owner_cum, 1)
        owner_poly1d = np.poly1d(owner_coef)
        
        # Project to 2030
        proj_years = np.array(range(int(yearly_data["Move-in Year"].max()) + 1, TARGET_YEAR + 1))
        
        if len(proj_years) > 0:
            owner_projections = owner_poly1d(proj_years)
            
            # Add projected line
            owner_fig.add_trace(go.Scatter(
                x=proj_years,
                y=owner_projections,
                mode="lines",
                name="Projected Owner Trend",
                line=dict(color="lightgreen", width=3, dash="dot")
            ))
            
            # Calculate and display projected deficit
            projected_owner_by_2030 = owner_poly1d(TARGET_YEAR)
            projected_owner_deficit = max(0, OWNER_GOAL - projected_owner_by_2030)
            
            if projected_owner_deficit > 0:
                owner_fig.add_annotation(
                    x=TARGET_YEAR,
                    y=projected_owner_by_2030,
                    text=f"Projected deficit: {int(projected_owner_deficit)} units",
                    showarrow=True,
                    arrowhead=1,
                    ax=50,
                    ay=-40,
                    font=dict(size=12, color="red"),
                    bordercolor="red",
                    bgcolor="white"
                )

    # Update owner chart layout
    owner_fig.update_layout(
        title="Owner Units Progress Toward 2030 Goal (220 Units)",
        xaxis_title="Year",
        yaxis_title="Owner Units",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450
    )

    st.plotly_chart(owner_fig, use_container_width=True)

# MAP OF PROJECTS (FULL WIDTH)
# ───────────────────────────────────────────────────────
st.subheader("Development Locations")

# Create columns for map and legend
map_col, legend_col = st.columns([5, 1])

with map_col:
    # Create a map centered on Portsmouth with a neutral color palette
    m = folium.Map(
        location=[43.07, -70.79], 
        zoom_start=13,
        tiles="CartoDB positron",  # Neutral grayscale base map
    )

    # Function to handle None/NaN values
    def safe_str(value):
        if pd.isna(value) or value == 0 or value is None:
            return "N/A"
        return str(value)

    # Function to create HTML link if URL exists
    def create_link(url, text):
        if pd.isna(url) or url == 0 or url is None or url == "":
            return "N/A"
        return f'<a href="{url}" target="_blank">{text}</a>'

    # Color mapping based on unit type majority
    def get_marker_color(row):
        if row["Rental Units"] > row["Owner Units"]:
            return "blue"  # Rental-dominant
        elif row["Owner Units"] > row["Rental Units"]:
            return "green"  # Owner-dominant
        else:
            return "purple"  # Mixed or equal

    # Add markers for each project
    for _, row in df.iterrows():
        # Skip if no location data
        if pd.isna(row["Latitude"]) or pd.isna(row["Longitude"]):
            continue
        
        # Prepare market rate status
        market_rate_status = "N/A"
        if not pd.isna(row["Market rate"]):
            market_rate_status = row["Market rate"]
        
        # Create enhanced popup content with links
        popup_html = f"""
        <div style="width: 300px; overflow-wrap: break-word;">
            <h4>{row['Project']}</h4>
            <b>Address:</b> {safe_str(row['Property address'])}<br>
            <b>Status:</b> {safe_str(row['Status'])}<br>
            <b>Move-in:</b> {safe_str(row['Move-in date'])}<br>
            <hr>
            <b>Housing Units:</b><br>
            <table style="width:100%">
                <tr>
                    <td>Rental Units:</td>
                    <td>{int(row['Rental Units'])}</td>
                </tr>
                <tr>
                    <td>Owner Units:</td>
                    <td>{int(row['Owner Units'])}</td>
                </tr>
                <tr>
                    <td><b>Total Units:</b></td>
                    <td><b>{int(row['Total units'])}</b></td>
                </tr>
            </table>
            <hr>
            <b>Market Rate:</b> {market_rate_status}<br>
            <b>City Project Info:</b> {create_link(row['City project info'], 'View Details')}<br>
            <b>Media Coverage:</b> {create_link(row['Media'], 'News Article')}<br>
            <br>
            {safe_str(row['Notes'])}
        </div>
        """
        
        # Use icon colors to distinguish between rental/owner developments
        folium.Marker(
            [row["Latitude"], row["Longitude"]],
            popup=folium.Popup(popup_html, max_width=350),
            tooltip=row['Project'],  # Show project name on hover
            icon=folium.Icon(color=get_marker_color(row))
        ).add_to(m)

    # Make map full width within its column
    folium_static(m, width=1000, height=500)

with legend_col:
    # Create a visual legend next to the map
    st.markdown("### Map Legend")
    
    # Project type colors
    st.markdown("""
    #### Project Types:
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 20px; height: 20px; background-color: blue; border-radius: 50%; margin-right: 10px;"></div>
        <div>Rental-dominant</div>
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 20px; height: 20px; background-color: green; border-radius: 50%; margin-right: 10px;"></div>
        <div>Owner-dominant</div>
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 20px; height: 20px; background-color: purple; border-radius: 50%; margin-right: 10px;"></div>
        <div>Mixed-use</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Project status explanation
    st.markdown("""
    #### How to Use:
    - **Click** on any marker to see project details
    - **Hover** over markers to see project names
    - Links in popups open in new tabs
    """)

# Additional summary for deficit tracking
st.subheader("Housing Goal Deficit Analysis")

# Create a table to show detailed deficit information
deficit_data = {
    "Housing Type": ["Rental Units", "Owner Units", "Total"],
    "2030 Goal": [RENTAL_GOAL, OWNER_GOAL, TOTAL_GOAL],
    "Current Planned": [int(current_rental), int(current_owner), int(current_rental + current_owner)],
    "Current Deficit": [int(rental_deficit), int(owner_deficit), int(total_deficit)]
}

if len(yearly_data) >= 2:
    # Calculate projections for 2030
    rental_projected = rental_poly1d(TARGET_YEAR) if 'rental_poly1d' in locals() else current_rental
    owner_projected = owner_poly1d(TARGET_YEAR) if 'owner_poly1d' in locals() else current_owner
    
    projected_rental_deficit = max(0, RENTAL_GOAL - rental_projected)
    projected_owner_deficit = max(0, OWNER_GOAL - owner_projected)
    projected_total_deficit = projected_rental_deficit + projected_owner_deficit
    
    deficit_data["Projected for 2030"] = [int(rental_projected), int(owner_projected), int(rental_projected + owner_projected)]
    deficit_data["Projected Deficit"] = [int(projected_rental_deficit), int(projected_owner_deficit), int(projected_total_deficit)]

deficit_df = pd.DataFrame(deficit_data)
st.table(deficit_df)

# Calculate units needed per year to meet goal
years_remaining = TARGET_YEAR - CURRENT_YEAR
if years_remaining > 0:
    rental_per_year = rental_deficit / years_remaining
    owner_per_year = owner_deficit / years_remaining
    
    st.info(f"**To meet the 2030 goals, Portsmouth needs to approve approximately:**\n"
            f"- **{int(rental_per_year)} new rental units per year**\n"
            f"- **{int(owner_per_year)} new owner units per year**\n"
            f"for the next {years_remaining} years.")