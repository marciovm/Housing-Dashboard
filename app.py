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

CSV_URL = (
    "https://docs.google.com/spreadsheets/d/"
    "1Ua0vVNtBNV5AR-tURo62lneVpeWCzN1J5LnkezCu2E4/"
    "export?format=csv&gid=751536993"
)

@st.cache_data(
    ttl=60,            # invalidate after 60 secs
    max_entries=500,     # keep the cache from ballooning
    show_spinner="Loading ..."
)

def load_data(path):
    return pd.read_csv(path)

# Load and preprocess data

def load_data(url: str) -> pd.DataFrame:
    """Download the latest data straight from Google Sheets."""
    return pd.read_csv(url)

df = load_data(CSV_URL)
df.fillna(0, inplace=True)  # Replace NaN with 0 for numeric calculations

# Define housing goals
RENTAL_GOAL = 2700
OWNER_GOAL = 220
TOTAL_GOAL = RENTAL_GOAL + OWNER_GOAL
TARGET_YEAR = 2030
CURRENT_YEAR = datetime.now().year

st.title("Portsmouth, NH Housing Dashboard")
st.subheader(f"Progress towards 2030 Housing Goal")
st.caption(f"Based on [PHA-commissioned 2022 study](https://www.portsmouthnh.gov/sites/default/files/2024-01/RKG_Portsmouth-Market-Analysis-FINAL_2022.pdf)")

# Create columns with consistent unit counts
df["Rental Units"] = df["Market Rate Rentals"] + df["Affordable Rentals"]
df["Owner Units"] = df["Market Rate Owner"] + df["Affordable Owner"]

# Add columns to clearly identify affordability mix
df["Affordable Units"] = df["Affordable Rentals"] + df["Affordable Owner"]
df["Market Rate Units"] = df["Market Rate Rentals"] + df["Market Rate Owner"]
df["Affordability Ratio"] = (df["Affordable Units"] / df["Total units"] * 100).fillna(0).round(1)

# Convert Expected finish to year and ensure it's numeric
df["Move-in Year"] = pd.to_numeric(df["Expected finish"], errors='coerce')

# Filter out rows with invalid years
df_valid = df[~pd.isna(df["Move-in Year"])].copy()

# Group by year
yearly_data = df_valid.groupby("Move-in Year").agg({
    "Rental Units": "sum",
    "Owner Units": "sum",
    "Total units": "sum",
    "Affordable Units": "sum",
    "Market Rate Units": "sum"
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
yearly_complete["Cumulative Affordable"] = yearly_complete["Affordable Units"].cumsum()
yearly_complete["Cumulative Market Rate"] = yearly_complete["Market Rate Units"].cumsum()

# Show current progress metrics
current_rental = yearly_complete["Cumulative Rental"].iloc[-1] if not yearly_complete.empty else 0
current_owner = yearly_complete["Cumulative Owner"].iloc[-1] if not yearly_complete.empty else 0
current_affordable = yearly_complete["Cumulative Affordable"].iloc[-1] if not yearly_complete.empty else 0
current_market_rate = yearly_complete["Cumulative Market Rate"].iloc[-1] if not yearly_complete.empty else 0

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
    affordable_percent = (current_affordable / (current_affordable + current_market_rate) * 100) if (current_affordable + current_market_rate) > 0 else 0
    st.metric("Affordable Housing", f"{int(current_affordable)} units", 
              f"{affordable_percent:.1f}% of all planned units")


# Housing Progress

# Create two-column layout for the charts
left_col, right_col = st.columns([1, 1])

# RENTAL UNITS CHART
with left_col:
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

# OWNER UNITS CHART
with right_col:
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




# Development Locations
st.header("Development Locations")


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

    # Color mapping based on affordability
    def get_marker_color(row):            
        if row["Affordability Ratio"] > 0:
            return "orange"  # affordability
        else:
            return "blue"    # Market rate only
        
    # Add markers for each project
    for _, row in df.iterrows():
        # Skip if no location data
        if pd.isna(row["Latitude"]) or pd.isna(row["Longitude"]):
            continue
        
        # Prepare market rate status
        market_rate_status = "N/A"
        if not pd.isna(row["Market rate"]):
            market_rate_status = row["Market rate"]
        
        # Calculate affordability percentage for this project
        affordability = row["Affordability Ratio"]
        
        # Create enhanced popup content with links
        popup_html = f"""
        <div style="width: 320px; overflow-wrap: break-word;">
            <h4>{row['Project']}</h4>
            <b>Address:</b> {safe_str(row['Property address'])}<br>
            <b>Status:</b> {safe_str(row['Status'])}<br>
            <b>Move-in:</b> {safe_str(row['Expected finish'])}<br>
            <hr>
            <b>Housing Units:</b><br>
            <table style="width:100%">
                <tr>
                    <td>Market Rate Units:</td>
                    <td>{int(row['Market Rate Units'])}</td>
                </tr>
                <tr>
                    <td>Affordable Units:</td>
                    <td>{int(row['Affordable Units'])}</td>
                </tr>
                <tr>
                    <td><b>Total Units:</b></td>
                    <td><b>{int(row['Total units'])}</b></td>
                </tr>
                <tr>
                    <td><b>Affordability:</b></td>
                    <td><b>{affordability:.1f}%</b></td>
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
        
        # Use icon colors to distinguish between affordability levels
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
    #### Affordability Levels:
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 20px; height: 20px; background-color: orange; border-radius: 50%; margin-right: 10px;"></div>
        <div>Permanently Affordable</div>
    </div>
    <div style="display: flex; align-items: center; margin-bottom: 10px;">
        <div style="width: 20px; height: 20px; background-color: skyblue; border-radius: 50%; margin-right: 10px;"></div>
        <div>Market Rate Only</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Usage instructions
    st.markdown("""
    #### How to Use:
    - **Click** on any marker to see project details
    - **Hover** over markers to see project names
    - Links in popups open in new tabs
    """)


# Market Rate vs. Affordable Housing
st.header("Market Rate vs. Affordable Housing")


# Create two-column layout
col1, col2 = st.columns([1, 1])

with col1:
    # Create a pie chart of total affordable vs market rate
    affordability_data = pd.DataFrame({
        "Housing Type": ["Market Rate Units", "Affordable Units"],
        "Count": [current_market_rate, current_affordable]
    })
    
    affordability_fig = px.pie(
        affordability_data, 
        values="Count", 
        names="Housing Type",
        title="Market Rate vs. Affordable Distribution",
        color_discrete_map={"Market Rate Units": "#1E88E5", "Affordable Units": "#FFC107"},
        hole=0.4
    )
    
    affordability_fig.update_layout(height=400)
    st.plotly_chart(affordability_fig, use_container_width=True)
    
with col2:
    # Create a bar chart showing affordability by project status
    affordability_by_status = df.groupby("Status").agg({
        "Market Rate Units": "sum",
        "Affordable Units": "sum"
    }).reset_index()
    
    affordability_status_fig = px.bar(
        affordability_by_status,
        x="Status",
        y=["Market Rate Units", "Affordable Units"],
        title="Affordability by Project Status",
        barmode="stack",
        category_orders={"Status": ["Potential", "Concept", "Design", "Permitting", "Approved", "Under construction"]},
        color_discrete_map={"Market Rate Units": "#1E88E5", "Affordable Units": "#FFC107"}
    )

    affordability_status_fig.update_layout(height=400)
    st.plotly_chart(affordability_status_fig, use_container_width=True)

# Project table with affordability percentages
st.subheader("Housing Projects by Affordability")

# Create a sorted dataframe for the table
affordable_table = df[~(df["Total units"] == 0)].copy()
affordable_table = affordable_table[["Project", "Total units", "Market Rate Units", 
                                     "Affordable Units", "Affordability Ratio", "Status", "Expected finish"]]
affordable_table = affordable_table.sort_values("Affordability Ratio", ascending=False)

# Add a column for affordability category
def categorize_affordability(ratio):
    if ratio > 0:            
        return "Affordable"
    else:
        return "Market Rate Only"

affordable_table["Affordability Category"] = affordable_table["Affordability Ratio"].apply(categorize_affordability)

# Display the table
st.dataframe(
    affordable_table[["Project", "Total units", "Affordable Units", 
                      "Affordability Ratio", "Affordability Category", "Status", "Expected finish"]],
    column_config={
        "Project": "Project Name",
        "Total units": "Total Units",
        "Affordable Units": "Affordable Units",
        "Affordability Ratio": st.column_config.NumberColumn(
            "Affordability %",
            format="%.1f%%"
        ),
        "Affordability Category": "Category",
        "Status": "Status",
        "Expected finish": "Expected Completion"
    },
    height=400
)

# Portsmouth Real Estate Market Trends (5-Year Overview)
st.header("Portsmouth Real Estate Market Trends (5-Year Overview)")


# Create two columns for home prices and rental prices
col1, col2 = st.columns([1, 1])

with col1:
    # Home price data for last 5 years (based on research)
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    median_home_prices = [650000, 720000, 775000, 830000, 850000, 859000]
    
    # Create home price trend chart
    home_price_fig = go.Figure()
    
    home_price_fig.add_trace(go.Scatter(
        x=years,
        y=median_home_prices,
        mode="lines+markers",
        name="Median Home Price",
        line=dict(color="#2E7D32", width=3)
    ))
    
    # Add annotations for the latest value
    home_price_fig.add_annotation(
        x=years[-1],
        y=median_home_prices[-1],
        text=f"${median_home_prices[-1]:,}",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40
    )
    
    # Calculate percentage increase over 5 years
    price_increase = ((median_home_prices[-1] - median_home_prices[0]) / median_home_prices[0]) * 100
    
    home_price_fig.update_layout(
        title=f"Median Home Sales Price (↑{price_increase:.1f}% over 5 years)",
        xaxis_title="Year",
        yaxis_title="Median Price ($)",
        yaxis=dict(tickformat="$,.0f"),
        height=450
    )
    
    st.plotly_chart(home_price_fig, use_container_width=True)
    
    st.markdown("""
    **Key Home Price Trends:**
    - Portsmouth median house value is $859,324, making it among the most expensive real estate in New Hampshire and America
    - The median sale price was $850K in January 2025, up 13.3% from the previous year
    - Portsmouth home prices increased by 10.2% year-over-year in February 2025
    """)
    
with col2:
    # Rental price data for last 5 years (based on research)
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    median_2br_rent = [1850, 1950, 2150, 2350, 2434, 2445]
    
    # Create rental price trend chart
    rent_price_fig = go.Figure()
    
    rent_price_fig.add_trace(go.Scatter(
        x=years,
        y=median_2br_rent,
        mode="lines+markers",
        name="Median 2BR Rent",
        line=dict(color="#1565C0", width=3)
    ))
    
    # Add annotations for the latest value
    rent_price_fig.add_annotation(
        x=years[-1],
        y=median_2br_rent[-1],
        text=f"${median_2br_rent[-1]:,}",
        showarrow=True,
        arrowhead=1,
        ax=40,
        ay=-40
    )
    
    # Calculate percentage increase over 5 years
    rent_increase = ((median_2br_rent[-1] - median_2br_rent[0]) / median_2br_rent[0]) * 100
    
    rent_price_fig.update_layout(
        title=f"Median 2-Bedroom Rental Price (↑{rent_increase:.1f}% over 5 years)",
        xaxis_title="Year",
        yaxis_title="Median Monthly Rent ($)",
        yaxis=dict(tickformat="$,.0f"),
        height=450
    )
    
    st.plotly_chart(rent_price_fig, use_container_width=True)
    
    st.markdown("""
    **Key Rental Trends:**
    - Average rent for an apartment in Portsmouth is $2,913, a 5% increase from last year
    - The average price for a two-bedroom apartment in Portsmouth is around $2,445
    - The average rent for a three bedroom apartment in Portsmouth is $2,582
    """)

    # Information sources and disclaimer
    st.markdown("""
    ---
    **Data Overview:** This section displays housing market trends in Portsmouth, NH based on recent real estate data. The charts show approximate trends based on aggregated data from multiple sources.
    
    **Note:** This is a placeholder section with estimated values. For precise, up-to-date market data, please consult with a real estate professional or economist.
    """)