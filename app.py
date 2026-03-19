import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Config
st.set_page_config(page_title="Strategic Data Prioritization Engine", layout="wide")

st.title("🚀 Strategic Digital Roadmap Engine")
st.markdown("""
    This tool transforms the **6-Pillar Data Audit** into an actionable decision framework. 
    Input new projects to calculate their strategic ROI and alignment.
""")

# 2. Sidebar: The "Audit Weights" (Global Strategy)
with st.sidebar:
    st.header("⚙️ Strategy Weighting")
    st.info("Adjust these based on current business focus (Total must = 100%)")
    w_impact = st.slider("Public User Impact (%)", 0, 50, 25)
    w_burden = st.slider("Staff Burden Reduction (%)", 0, 50, 20)
    w_ai = st.slider("AI Leverage Potential (%)", 0, 50, 20)
    w_reach = st.slider("System-wide Reach (%)", 0, 50, 20)
    w_ready = st.slider("Deliverability/Readiness (%)", 0, 50, 15)
    
    total_w = w_impact + w_burden + w_ai + w_reach + w_ready
    if total_w != 100:
        st.error(f"Total Weight: {total_w}% (Must be 100%)")

# 3. Main Input Section
st.subheader("📝 Project Evaluation")
col1, col2 = st.columns(2)

with col1:
    project_name = st.text_input("Project Name", placeholder="e.g., Tribunal Portal AI Chatbot")
    is_legal = st.toggle("⚖️ Statutory/Legal Obligation?", help="If checked, this project bypasses ROI scoring and moves to P0.")

with col2:
    project_desc = st.text_area("Description/AOI", placeholder="Which Area of Interest does this solve?")

st.divider()

# 4. The 6-Pillar Scoring Logic
st.write("### 📊 Scoring (Scale 1-10)")
c1, c2, c3, c4, c5 = st.columns(5)

with c1: s_impact = st.number_input("User Impact", 1, 10, 5)
with c2: s_burden = st.number_input("Staff Relief", 1, 10, 5)
with c3: s_ai = st.number_input("AI Readiness", 1, 10, 5)
with c4: s_reach = st.number_input("Cross-System", 1, 10, 5)
with c5: s_ready = st.number_input("Ease of Build", 1, 10, 5)

# 5. The Calculation
# Formula: (Score * Weight) / 100
final_score = (
    (s_impact * w_impact) + 
    (s_burden * w_burden) + 
    (s_ai * w_ai) + 
    (s_reach * w_reach) + 
    (s_ready * w_ready)
) / 10

# 6. Display Result
st.divider()
res_col1, res_col2 = st.columns([1, 2])

with res_col1:
    st.metric("Strategic ROI Score", f"{final_score:.2f} / 10")
    
    if is_legal:
        st.error("RANK: P0 - MANDATORY (LEGAL)")
    elif final_score >= 7.5:
        st.success("RANK: P1 - STRATEGIC PRIORITY")
    elif final_score >= 5.0:
        st.warning("RANK: P2 - OPPORTUNISTIC")
    else:
        st.info("RANK: P3 - BACKLOG / DE-PRIORITIZE")

with res_col2:
    # Quick Visualization of the specific project "shape"
    chart_data = pd.DataFrame(dict(
        r=[s_impact, s_burden, s_ai, s_reach, s_ready],
        theta=['User Impact','Staff Relief','AI Readiness','Reach','Deliverability']))
    fig = px.line_polar(chart_data, r='r', theta='theta', line_close=True)
    fig.update_traces(fill='toself')
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("Developed as part of the Web Data Audit & Strategy Framework - 2026")
