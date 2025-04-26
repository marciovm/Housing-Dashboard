# geocode_addresses.py

import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

def batch_geocode(input_csv, output_csv, address_col="Property address"):
    # 1. Load your data
    df = pd.read_csv(input_csv)

    # 2. Set up Nominatim with a custom user_agent
    geolocator = Nominatim(user_agent="portsmouth_housing_geocoder")
    # RateLimiter to respect 1 request/sec
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    # 3. Do the geocoding
    # Create placeholder columns
    df["Latitude"] = None
    df["Longitude"] = None

    for idx, row in df.iterrows():
        addr = row[address_col]
        if pd.isna(addr):
            continue

        try:
            location = geocode(addr)
            if location:
                df.at[idx, "Latitude"]  = location.latitude
                df.at[idx, "Longitude"] = location.longitude
        except Exception as e:
            # If it fails, sleep briefly and retry once
            print(f"Error geocoding row {idx} ({addr}): {e}")
            time.sleep(2)
            try:
                location = geocode(addr)
                if location:
                    df.at[idx, "Latitude"]  = location.latitude
                    df.at[idx, "Longitude"] = location.longitude
            except Exception as e2:
                print(f"  Retry failed: {e2}")
        # (Optional) print progress every 50
        if idx % 50 == 0:
            print(f"Processed {idx}/{len(df)} addresses")

    # 4. Save enriched CSV
    df.to_csv(output_csv, index=False)
    print(f"✅ Saved geocoded data to {output_csv}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Batch geocode addresses with geopy")
    parser.add_argument("input_csv",  help="Path to input CSV file")
    parser.add_argument("output_csv", help="Path for output CSV file")
    args = parser.parse_args()

    batch_geocode(args.input_csv, args.output_csv)
