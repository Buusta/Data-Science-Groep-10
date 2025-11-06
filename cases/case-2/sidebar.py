import streamlit as st
import os
from datetime import datetime

APIFY_RUN_URL = "https://console.apify.com/actors/m7QkAOpTRBj8Jszlv/runs/dKKMXQjeUTZPbp2hh#output"

def render_sidebar():
    """Render shared sidebar with source info and dataset refresh button."""
    from dashboard import fetch_latest_data, LOCAL_CSV
    st.sidebar.header("Dataset Management")

    # Show last updated time
    if os.path.exists(LOCAL_CSV):
        modified_time = datetime.fromtimestamp(os.path.getmtime(LOCAL_CSV))
        st.sidebar.caption(f"📅 Last update: {modified_time.strftime('%d %b %Y, %H:%M')}")

    st.sidebar.markdown("---")
    st.sidebar.caption(f"**Source:** [Apify Steam Store Scraper]({APIFY_RUN_URL})")
    st.sidebar.caption("ActID: `m0uka~steam-store-scraper`")

    # Initialize session_state flag if not present
    if "refresh_requested" not in st.session_state:
        st.session_state.refresh_requested = False

    # Refresh button
    if st.sidebar.button("🔄 Refresh dataset"):
        st.session_state.refresh_requested = True

    # Conditionally fetch new data
    if st.session_state.refresh_requested:
        st.sidebar.info("Fetching new data from Steam... (~1 min)")
        try:
            df_new = fetch_latest_data()
            if not df_new.empty:
                df_new.to_csv(LOCAL_CSV, index=False)
                st.sidebar.success(f"Dataset successfully refreshed! ({len(df_new)} games)")
            else:
                st.sidebar.error("Could not fetch new data (empty dataset).")
        except Exception as e:
            st.sidebar.error(f"Error fetching data: {e}")
        finally:
            st.session_state.refresh_requested = False
