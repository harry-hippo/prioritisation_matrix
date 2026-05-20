import streamlit as st
import pandas as pd
import plotly.express as px
import time
from streamlit_gsheets import GSheetsConnection

# --- 1. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="NHS App Prioritisation Tool", layout="wide")

st.title("NHS App & Digital Services Prioritisation Matrix")
st.markdown("""
**Vision:** Enabling confident, equitable, evidence-based actions that drive widespread adoption of the NHS App and related digital services.  
**Mission:** To equip NHS staff with trusted insights that explain variation, identify barriers, and provide actionable recommendations that drive system-level change.
""")
st.divider()

# --- 2. GOOGLE SHEETS SETUP ---
SHEET_ID = "1b3rZT7-WdKVi-AKM6I4a53ylPrmLlErSZ-UtR1i8Jzw"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"

# --- 3. SESSION STATE DATA CACHING (Load Once) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_read_sheet(conn, retries=3, base_wait=1):
    for i in range(retries):
        try:
            return conn.read()
        except Exception as e:
            err_text = str(e)
            if any(x in err_text for x in ["RATE_LIMIT_EXCEEDED", "Read requests", "RESOURCE_EXHAUSTED"]):
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

# --- 4. SIDEBAR: GLOBAL STRATEGY WEIGHTS ---
with st.sidebar:
    st.header("Strategy Weighting")
    st.info("Adjust weights to reflect priorities. Sliders default to the baseline framework distribution.")
    
    w_insight = st.slider("Insight Value (%)", 0, 50, 10)
    w_reusage = st.slider("Re-usability / Cross-Team Benefit (%)", 0, 50, 20)
    w_alignment = st.slider("Strategic Alignment (%)", 0, 50, 20)
    w_equity = st.slider("Equity, Inequalities & Systemic Importance (%)", 0, 50, 30)
    w_feasibility = st.slider("Delivery Feasibility / Readiness (%)", 0, 50, 20)
    
    total_w = w_insight + w_reusage + w_alignment + w_equity + w_feasibility
    
    if total_w != 100:
        st.error(f"Total: {total_w}% (Must equal 100%)")
    else:
        st.success("Weights Balanced (100%)")

# --- 5. MAIN CONTENT APP LOGIC ---
if total_w != 100:
    st.warning("⚠️ Please adjust the sidebar strategy weights so they total exactly 100% to activate the evaluation dashboard.")
else:
    # --- PROJECT INPUT SECTION ---
    st.subheader("New Request / Project Evaluation")
    col_in1, col_in2 = st.columns(2)

    with col_in1:
        project_name = st.text_input("Project / Request Name", placeholder="e.g., Demographics Variation Dashboard")
        is_legal = st.toggle("Statutory / Mandatory Obligation?", help="Bypasses standard framework scoring directly to P0 Priority.")

    with col_in2:
        project_desc = st.text_area("Strategic Context", placeholder="How does this request explain variation or provide actionable recommendations?")
        effort_notes = st.text_area("Size / Effort Notes (Refinement)", placeholder="Notes regarding effort from a DA (Data Analyst), UR (User Research), and BA (Business Analyst) perspective...")

    st.divider()

    # --- THE SCORING PILLARS (Scale 1-5) ---
    st.write("### Framework Pillar Scoring (Scale 1-5)")
    c1, c2, c3, c4, c5 = st.columns(5)

    with c1: 
        s_insight = st.number_input("Insight Value", 1, 5, 3, 
                                    help="1 = Low impact / informational only\n5 = High impact / highly actionable insight")
    with c2: 
        s_reusage = st.number_input("Re-usability", 1, 5, 3, 
                                    help="1 = Beneficial for a single team\n5 = Could be used by multiple teams")
    with c3: 
        s_alignment = st.number_input("Strategic Alignment", 1, 5, 3, 
                                      help="1 = Limited relevance\n5 = Directly aligned to strategic adoption priorities")
    with c4: 
        s_equity = st.number_input("Equity & Systemic", 1, 5, 3, 
                                   help="1 = No equity angle\n5 = Has strong potential to improve equitable adoption / address gaps")
    with c5: 
        s_feasibility = st.number_input("Delivery Feasibility", 1, 5, 3, 
                                        help="1 = Low feasibility / unreliable data\n5 = High feasibility / data available & clear metrics")

    # Calculate weighted score (normalized to 1-5 scale)
    final_score = round(((s_insight * w_insight) + (s_reusage * w_reusage) + 
                         (s_alignment * w_alignment) + (s_equity * w_equity) + (s_feasibility * w_feasibility)) / 100, 2)

    # --- VISUALIZATION & RESULTS ---
    st.divider()
    res_col1, res_col2 = st.columns([1, 2])

    with res_col1:
        st.metric("Strategic Value Score", f"{final_score:.2f} / 5.00")
        
        if is_legal:
            st.error("RANK: P0 - MANDATORY")
            priority_label = "P0 - Mandatory"
        elif final_score >= 3.75:
            st.success("RANK: P1 - HIGH PRIORITY")
            priority_label = "P1 - High"
        elif final_score >= 2.50:
            st.warning("RANK: P2 - OPPORTUNISTIC")
            priority_label = "P2 - Medium"
        else:
            st.info("RANK: P3 - BACKLOG")
            priority_label = "P3 - Low"

    with res_col2:
        # Radar Chart mapping standard 1-5 scale limits
        df_radar = pd.DataFrame(dict(
            r=[s_insight, s_reusage, s_alignment, s_equity, s_feasibility],
            theta=['Insight Value', 'Re-usability', 'Strategic Alignment', 'Equity & Systemic', 'Delivery Feasibility']
        ))
        fig = px.line_polar(df_radar, r='r', theta='theta', line_close=True)
        fig.update_traces(fill='toself', line_color='#005EB8') # Official NHS Corporate Blue
        fig.update_polars(radialaxis=dict(range=[0, 5], gridcolor="lightgrey"))
        st.plotly_chart(fig, use_container_width=True)

    # --- DATABASE OPERATIONS (SAVE) ---
    if st.button("Save Request to Roadmap"):
        if not project_name.strip():
            st.error("Please enter a Project/Request Name before saving.")
        else:
            try:
                new_row = pd.DataFrame([{
                    "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                    "Project": project_name,
                    "Score": final_score,
                    "Priority": priority_label,
                    "Context": project_desc,
                    "Effort Notes": effort_notes
                }])
                
                existing_df = st.session_state.roadmap_df
                updated_df = pd.concat([existing_df, new_row], ignore_index=True)
                
                conn.update(data=updated_df)
                st.session_state.roadmap_df = updated_df
                
                st.success(f"Successfully added '{project_name}' to the Roadmap Portfolio!")
                st.balloons()
            except Exception as e:
                st.error(f"Error saving to Google Sheets: {e}")

# --- 6. LIVE PORTFOLIO LEADERBOARD VIEW ---
st.divider()
st.subheader("Master Digital Roadmap Portfolio")

df_view = st.session_state.get("roadmap_df", pd.DataFrame())
if not df_view.empty:
    st.dataframe(
        df_view.sort_values(by="Score", ascending=False),
        use_container_width=True,
        column_config={
            "Score": st.column_config.ProgressColumn(
                "Strategic Score",
                help="Weighted prioritization calculation out of 5.00 max",
                format="%.2f",
                min_value=1,
                max_value=5
            ),
            "Timestamp": st.column_config.DatetimeColumn("Date Logged", format="D MMM YYYY, h:mm a"),
            "Priority": st.column_config.TextColumn("Priority Category"),
            "Project": st.column_config.TextColumn("Project / Request Name"),
            "Context": st.column_config.TextColumn("Strategic Context"),
            "Effort Notes": st.column_config.TextColumn("Refinement Details (DA/UR/BA)")
        }
    )
else:
    st.info("The Master Roadmap portfolio is currently empty. Add your first digital initiative assessment above!")

st.caption("NHS App Adoption Strategy Tool v3.0 | Powered by Streamlit & Google Sheets")


# --- 7. ADMIN CONTROLS ---
st.divider()
with st.expander("🛠️ Admin Controls"):
    st.info("This area is restricted. Please enter the admin password to access database controls.")
    
    # The type="password" argument masks the input with dots
    pwd_input = st.text_input("Admin Password", type="password")
    
    if pwd_input:
        # Check if it matches the password in secrets.toml
        if pwd_input == st.secrets["admin_password"]:
            st.success("Access Granted.")
            st.warning("⚠️ DANGER: This will permanently delete all projects from the Google Sheet.")
            
            if st.button("Clear All Roadmap Data", type="primary"):
                empty_df = pd.DataFrame(columns=[
                    "Timestamp", "Project", "Score", "Priority", "Context", "Effort Notes"
                ])
                try:
                    conn.update(data=empty_df)
                    st.session_state.roadmap_df = empty_df
                    st.success("Roadmap cleared successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to clear data: {e}")
        else:
            st.error("Incorrect password.")
