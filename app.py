import streamlit as st
import pandas as pd
import plotly.express as px
import time
from streamlit_gsheets import GSheetsConnection

# --- 1. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="Strategic Digital Roadmap", layout="wide")

st.title("Strategic Digital Roadmap Prioritisaion")
st.markdown("""
This tool converts your project evaluation inputs into an actionable prioritisation framework. \n
Prioritise projects based on User Impact, Staff Burden Reduction, AI Leverage Potential, System-wide Reach, and Deliverability/Readiness.
""")

# --- 2. GOOGLE SHEETS SETUP ---
# Use the spreadsheet ID to avoid /edit URL artifacts and 404 mismatches.
SHEET_ID = "1b3rZT7-WdKVi-AKM6I4a53ylPrmLlErSZ-UtR1i8Jzw"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"

# --- 3. SIDEBAR: GLOBAL STRATEGY WEIGHTS ---
with st.sidebar:
    st.header("Strategy Weighting")
    st.info("Adjust weights to reflect this quarter's business priorities.")
    
    w_impact = st.slider("Public User Impact (%)", 0, 50, 25)
    w_burden = st.slider("Staff Burden Reduction (%)", 0, 50, 20)
    w_ai = st.slider("AI Leverage Potential (%)", 0, 50, 20)
    w_reach = st.slider("System-wide Reach (%)", 0, 50, 20)
    w_ready = st.slider("Deliverability/Readiness (%)", 0, 50, 15)
    
    total_w = w_impact + w_burden + w_ai + w_reach + w_ready
    if total_w != 100:
        st.error(f"Total: {total_w}% (Must be 100%)")
    else:
        st.success("Weights Balanced")

# --- 4. PROJECT INPUT SECTION ---
st.subheader("New Project Evaluation")
col_in1, col_in2 = st.columns(2)

with col_in1:
    project_name = st.text_input("Project Name", placeholder="e.g., GA4-BigQuery Integration")
    is_legal = st.toggle("Statutory/Legal Obligation?", help="Bypasses ROI score to P0 Priority.")

with col_in2:
    project_desc = st.text_area("Strategic Context", placeholder="How does this align with Business AOIs?")

st.divider()

# --- 5. THE SCORING PILLARS ---
st.write("### Pillar Scoring (Scale 1-10)")
c1, c2, c3, c4, c5 = st.columns(5)

with c1: s_impact = st.number_input("User Impact", 1, 10, 5)
with c2: s_burden = st.number_input("Staff Relief", 1, 10, 5)
with c3: s_ai = st.number_input("AI Readiness", 1, 10, 5)
with c4: s_reach = st.number_input("Reach", 1, 10, 5)
with c5: s_ready = st.number_input("Readiness", 1, 10, 5)

# Calculate weighted score (normalized to 0-10 scale)
final_score = ((s_impact * w_impact) + (s_burden * w_burden) + 
               (s_ai * w_ai) + (s_reach * w_reach) + (s_ready * w_ready)) / 100

# --- 6. VISUALIZATION & RESULTS ---
st.divider()
res_col1, res_col2 = st.columns([1, 2])

with res_col1:
    st.metric("Strategic Value Score", f"{final_score:.2f} / 10")
    
    if is_legal:
        st.error("RANK: P0 - MANDATORY")
        priority_label = "P0 - Mandatory"
    elif final_score >= 7.5:
        st.success("RANK: P1 - HIGH PRIORITY")
        priority_label = "P1 - High"
    elif final_score >= 5.0:
        st.warning("RANK: P2 - OPPORTUNISTIC")
        priority_label = "P2 - Medium"
    else:
        st.info("RANK: P3 - BACKLOG")
        priority_label = "P3 - Low"

with res_col2:
    # Radar Chart
    df_radar = pd.DataFrame(dict(
        r=[s_impact, s_burden, s_ai, s_reach, s_ready],
        theta=['User Impact','Staff Relief','AI Readiness','Reach','Readiness']))
    fig = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
    fig.update_traces(fill='toself', line_color='#FF4B4B')
    st.plotly_chart(fig, use_container_width=True)

# --- 7. DATABASE OPERATIONS (SAVE & VIEW) ---
st.divider()
st.subheader("Master Digital Roadmap")

# 1. Initialize Connection
# Note: It automatically looks for [connections.gsheets] in secrets.toml
conn = st.connection("gsheets", type=GSheetsConnection)

# 2. Safety Check: Verify Service Account Email (Optional/Debug)
try:
    sa_email = st.secrets["connections"]["gsheets"]["client_email"]
    st.caption(f"Connected via: {sa_email}")
except Exception as err:
    st.error(f"Secrets not found or invalid. Check .streamlit/secrets.toml: {err}")

# Utility: Read with quota retry and caching in session state

def safe_read_sheet(conn, retries=3, base_wait=1):
    for i in range(retries):
        try:
            return conn.read()
        except Exception as e:
            err_text = str(e)
            if "RATE_LIMIT_EXCEEDED" in err_text or "Read requests" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                if i < retries - 1:
                    wait = base_wait * (2 ** i)
                    st.warning(f"Rate limit hit, retrying in {wait}s ({i+1}/{retries})...")
                    time.sleep(wait)
                    continue
            raise


if "roadmap_df" not in st.session_state:
    try:
        st.session_state.roadmap_df = safe_read_sheet(conn)
    except Exception as e:
        st.session_state.roadmap_df = pd.DataFrame()
        st.warning(f"Could not read roadmap from sheet: {e}")

# 3. Button to Save Data
if st.button("Save Project to Roadmap"):
    if not project_name.strip():
        st.error("Please enter a Project Name before saving.")
    elif total_w != 100:
        st.error("Weights must equal 100% to save.")
    else:
        try:
            new_row = pd.DataFrame([{
                "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                "Project": project_name,
                "Score": final_score,
                "Priority": priority_label,
                "Description": project_desc
            }])
            
            # Read existing data (use cached session-state copy when available)
            existing_df = st.session_state.get("roadmap_df")
            if existing_df is None or existing_df.empty:
                existing_df = safe_read_sheet(conn)

            # Append and Update
            updated_df = pd.concat([existing_df, new_row], ignore_index=True)
            conn.update(data=updated_df)

            st.session_state.roadmap_df = updated_df
            st.success(f"Successfully added '{project_name}' to the Roadmap!")
            st.balloons()
        except Exception as e:
            st.error(f"Error saving to Google Sheets: {e}")

# 4. Live Leaderboard View
st.write("#### Current Portfolio View")

if "roadmap_df" not in st.session_state or st.session_state.roadmap_df is None:
    try:
        st.session_state.roadmap_df = safe_read_sheet(conn)
    except Exception as e:
        st.warning(f"Could not load roadmap table: {e}")

try:
    df_view = st.session_state.get("roadmap_df", pd.DataFrame())
    if not df_view.empty:
        st.dataframe(df_view.sort_values(by="Score", ascending=False), use_container_width=True)
    else:
        st.info("The Roadmap is currently empty. Add your first project above!")
except Exception as e:
    st.warning(f"Could not display roadmap table: {e}")

st.caption("Data Audit Strategy Tool v2.1 | Powered by Streamlit & Google Sheets")