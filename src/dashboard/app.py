"""
Sentinel Dashboard - Main Streamlit Application
AI-powered surveillance system for prediction market integrity
"""
import streamlit as st
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Sentinel",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    /* Dark theme adjustments */
    .stApp {
        background-color: #0e1117;
    }

    /* Classification badges */
    .insider-badge {
        background-color: #ff4b4b;
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: bold;
    }
    .osint-badge {
        background-color: #00cc66;
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: bold;
    }
    .reactor-badge {
        background-color: #ffa500;
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: bold;
    }
    .speculator-badge {
        background-color: #6c757d;
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: bold;
    }

    /* Metric cards */
    .metric-card {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }

    /* Temporal gap chart styling */
    .temporal-chart {
        background-color: #1e2130;
        padding: 20px;
        border-radius: 10px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def get_classification_badge(classification: str) -> str:
    """Return HTML badge for classification."""
    badges = {
        "INSIDER": '<span class="insider-badge">🚨 INSIDER</span>',
        "OSINT_EDGE": '<span class="osint-badge">🔍 OSINT EDGE</span>',
        "FAST_REACTOR": '<span class="reactor-badge">⚡ FAST REACTOR</span>',
        "SPECULATOR": '<span class="speculator-badge">🎲 SPECULATOR</span>',
    }
    return badges.get(classification, classification)


def main():
    # Sidebar
    with st.sidebar:
        st.image("https://img.icons8.com/ios-filled/100/ffffff/shield.png", width=60)
        st.title("SENTINEL")
        st.caption("Prediction Market Integrity Monitor")

        st.divider()

        # Navigation
        page = st.radio(
            "Navigation",
            ["🏠 Dashboard", "🔍 Case Detail", "📊 Sentinel Index", "⚖️ Arena", "🏥 System Health"],
            label_visibility="collapsed"
        )

        st.divider()

        # Quick stats
        from src.data.database import get_connection, get_stats
        conn = get_connection()
        stats = get_stats(conn)
        conn.close()

        st.metric("Total Cases", stats['total_cases'])
        st.metric("Anomalies Detected", stats['total_anomalies'])

        # Classification breakdown
        if stats['cases_by_classification']:
            st.caption("Cases by Type")
            for cls, count in stats['cases_by_classification'].items():
                color = {
                    "INSIDER": "🔴",
                    "OSINT_EDGE": "🟢",
                    "FAST_REACTOR": "🟠",
                    "SPECULATOR": "⚪"
                }.get(cls, "⚪")
                st.text(f"{color} {cls}: {count}")

    # Main content
    if page == "🏠 Dashboard":
        show_dashboard()
    elif page == "🔍 Case Detail":
        show_case_detail()
    elif page == "📊 Sentinel Index":
        show_sentinel_index()
    elif page == "⚖️ Arena":
        show_arena()
    elif page == "🏥 System Health":
        show_system_health()


def show_dashboard():
    """Main dashboard / live monitor view."""
    st.title("🛡️ Sentinel Dashboard")
    st.caption("Real-time anomaly detection for prediction markets")

    # Key metrics row
    from src.data.database import (
        get_connection,
        get_stats,
        list_anomalies,
        list_evidence_packets,
    )
    import pandas as pd
    conn = get_connection()
    stats = get_stats(conn)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        insider_count = stats['cases_by_classification'].get('INSIDER', 0)
        st.metric("🚨 Insider Cases", insider_count, delta=None)
    with col2:
        osint_count = stats['cases_by_classification'].get('OSINT_EDGE', 0)
        st.metric("🔍 OSINT Edge", osint_count)
    with col3:
        st.metric("📈 Total Anomalies", stats['total_anomalies'])
    with col4:
        confirmed = stats['cases_by_status'].get('CONFIRMED', 0)
        st.metric("✅ Confirmed Cases", confirmed)

    st.divider()

    # Recent anomalies
    st.subheader("Recent Anomalies")

    # Filter
    col1, col2 = st.columns([1, 3])
    with col1:
        filter_class = st.selectbox(
            "Filter by classification",
            ["All", "INSIDER", "OSINT_EDGE", "FAST_REACTOR", "SPECULATOR"]
        )

    anomalies = list_anomalies(
        conn,
        classification=filter_class if filter_class != "All" else None,
        limit=20
    )
    evidence_packets = list_evidence_packets(conn, limit=20)
    conn.close()

    if not anomalies:
        st.info("No anomalies detected yet. Run the data pipeline to start monitoring.")
    else:
        for anomaly in anomalies:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                with col1:
                    st.markdown(f"**{anomaly['market_name']}**")
                    st.caption(f"Event ID: {anomaly['event_id']}")
                with col2:
                    st.markdown(get_classification_badge(anomaly['classification']), unsafe_allow_html=True)
                with col3:
                    st.metric("BSS", anomaly['bss_score'], label_visibility="collapsed")
                with col4:
                    st.metric("Z-Score", f"{anomaly['z_score']:.1f}", label_visibility="collapsed")
                st.divider()

    st.subheader("🧩 Live Evidence Packets")
    if not evidence_packets:
        st.info("No evidence packets yet. Run `python main.py monitor --mock` to generate live packets.")
    else:
        packets_df = pd.DataFrame(evidence_packets)
        packets_df = packets_df[
            [
                "case_id",
                "market_name",
                "wallet_address",
                "trade_timestamp",
                "temporal_gap_minutes",
                "temporal_gap_score",
                "wallet_risk_score",
                "cluster_size",
                "correlation_score",
            ]
        ]
        packets_df.columns = [
            "Case ID",
            "Market",
            "Wallet",
            "Trade Time",
            "Gap (min)",
            "Gap Score",
            "Wallet Risk",
            "Cluster Size",
            "Correlation",
        ]
        st.dataframe(
            packets_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Gap Score": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0, format="%.2f"),
                "Wallet Risk": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0, format="%.2f"),
                "Correlation": st.column_config.ProgressColumn(min_value=0.0, max_value=1.0, format="%.2f"),
            },
        )


def show_case_detail():
    """Case detail view with temporal gap chart."""
    st.title("🔍 Case Detail")

    from src.data.database import get_connection, list_cases, get_case, get_anomaly, get_osint_events_in_range
    import json
    import plotly.graph_objects as go
    from datetime import datetime, timedelta

    conn = get_connection()
    cases = list_cases(conn, limit=100)

    if not cases:
        st.info("No cases in the Sentinel Index yet.")
        conn.close()
        return

    # Case selector
    case_options = {f"{c['case_id']} - {c['market_name'][:50]}": c['case_id'] for c in cases}
    selected = st.selectbox("Select a case", list(case_options.keys()))
    case_id = case_options[selected]

    case = get_case(conn, case_id)
    anomaly = get_anomaly(conn, case['anomaly_event_id']) if case['anomaly_event_id'] else None

    if not case:
        st.error("Case not found")
        conn.close()
        return

    # Case header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"## {case['market_name']}")
        st.markdown(get_classification_badge(case['classification']), unsafe_allow_html=True)
    with col2:
        st.metric("BSS Score", f"{case['bss_score']}/100")
    with col3:
        st.metric("PES Score", f"{case['pes_score']}/100")

    st.divider()

    # ===================
    # TEMPORAL GAP CHART - The key visualization
    # ===================
    st.subheader("📊 Temporal Gap Analysis")
    st.caption("When did the trade occur relative to public information?")

    # Parse evidence
    evidence = json.loads(case['evidence_json']) if case['evidence_json'] else {}

    # Create timeline data
    trade_time = datetime.fromisoformat(evidence.get('trade_timestamp', datetime.now().isoformat()))
    news_time = datetime.fromisoformat(evidence['news_timestamp']) if evidence.get('news_timestamp') else None

    # Build the temporal gap chart
    fig = go.Figure()

    # Calculate time range
    min_time = trade_time - timedelta(hours=24)
    max_time = trade_time + timedelta(hours=24)

    if news_time:
        min_time = min(min_time, news_time - timedelta(hours=2))
        max_time = max(max_time, news_time + timedelta(hours=2))

    # Add OSINT signals as green circles
    osint_signals = evidence.get('osint_signals', [])
    for signal in osint_signals:
        signal_time = trade_time - timedelta(hours=signal['hours_before_trade'])
        fig.add_trace(go.Scatter(
            x=[signal_time],
            y=[0.5],
            mode='markers+text',
            marker=dict(size=20, color='#00cc66', symbol='circle'),
            text=[f"📰 {signal['source']}"],
            textposition="top center",
            name=f"OSINT: {signal['headline'][:30]}...",
            hovertemplate=f"<b>{signal['source']}</b><br>{signal['headline']}<br>%{{x}}<extra></extra>"
        ))

    # Add trade as red diamond
    fig.add_trace(go.Scatter(
        x=[trade_time],
        y=[0.5],
        mode='markers+text',
        marker=dict(size=30, color='#ff4b4b', symbol='diamond'),
        text=["💰 TRADE"],
        textposition="top center",
        name="Suspicious Trade",
        hovertemplate=f"<b>Trade Executed</b><br>${evidence.get('trade_size_usd', 0):,.0f}<br>%{{x}}<extra></extra>"
    ))

    # Add news break as orange star
    if news_time:
        fig.add_trace(go.Scatter(
            x=[news_time],
            y=[0.5],
            mode='markers+text',
            marker=dict(size=25, color='#ffa500', symbol='star'),
            text=["📢 NEWS"],
            textposition="top center",
            name="News Announcement",
            hovertemplate=f"<b>News Break</b><br>{evidence.get('news_headline', 'Unknown')}<br>%{{x}}<extra></extra>"
        ))

    # Add "Information Gap" zone for INSIDER cases
    if case['classification'] == 'INSIDER' and news_time and trade_time < news_time:
        fig.add_vrect(
            x0=trade_time,
            x1=news_time,
            fillcolor="rgba(255, 75, 75, 0.2)",
            layer="below",
            line_width=0,
            annotation_text="⚠️ NO PUBLIC INFORMATION",
            annotation_position="top",
        )

    # Layout
    fig.update_layout(
        title="Temporal Gap Timeline",
        xaxis_title="Time",
        yaxis=dict(visible=False, range=[0, 1]),
        height=300,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Temporal gap metric
    if case['temporal_gap_hours']:
        gap_hours = abs(case['temporal_gap_hours'])
        if case['classification'] == 'INSIDER':
            st.error(f"⚠️ **CRITICAL**: Trade was placed **{gap_hours:.1f} hours BEFORE** any public information existed.")
        elif case['classification'] == 'OSINT_EDGE':
            st.success(f"✅ Trade was placed **{gap_hours:.1f} hours AFTER** public signals became available.")

    st.divider()

    # 2x2 Classification Grid
    st.subheader("📈 Classification Grid")
    col1, col2 = st.columns(2)

    with col1:
        # BSS vs PES scatter
        fig2 = go.Figure()

        # Add quadrant backgrounds
        fig2.add_shape(type="rect", x0=0, y0=50, x1=50, y1=100, fillcolor="rgba(0,204,102,0.2)", line_width=0)  # OSINT
        fig2.add_shape(type="rect", x0=50, y0=50, x1=100, y1=100, fillcolor="rgba(255,165,0,0.2)", line_width=0)  # Reactor
        fig2.add_shape(type="rect", x0=0, y0=0, x1=50, y1=50, fillcolor="rgba(108,117,125,0.2)", line_width=0)  # Speculator
        fig2.add_shape(type="rect", x0=50, y0=0, x1=100, y1=50, fillcolor="rgba(255,75,75,0.2)", line_width=0)  # Insider

        # Add the case point
        fig2.add_trace(go.Scatter(
            x=[case['bss_score']],
            y=[case['pes_score']],
            mode='markers',
            marker=dict(size=20, color='white', line=dict(color='#ff4b4b', width=3)),
            name="This Case"
        ))

        # Add labels
        fig2.add_annotation(x=25, y=75, text="OSINT_EDGE", showarrow=False, font=dict(color='#00cc66', size=14))
        fig2.add_annotation(x=75, y=75, text="FAST_REACTOR", showarrow=False, font=dict(color='#ffa500', size=14))
        fig2.add_annotation(x=25, y=25, text="SPECULATOR", showarrow=False, font=dict(color='#6c757d', size=14))
        fig2.add_annotation(x=75, y=25, text="INSIDER", showarrow=False, font=dict(color='#ff4b4b', size=14))

        fig2.update_layout(
            xaxis_title="Behavioral Suspicion Score (BSS)",
            yaxis_title="Public Explainability Score (PES)",
            xaxis=dict(range=[0, 100]),
            yaxis=dict(range=[0, 100]),
            height=350,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
        )

        st.plotly_chart(fig2, use_container_width=True)

    with col2:
        # Fraud Triangle
        st.markdown("### 🔺 Fraud Triangle Analysis")
        if anomaly and anomaly.get('fraud_triangle_json'):
            fraud = json.loads(anomaly['fraud_triangle_json'])
            st.markdown(f"**Pressure:** {fraud.get('pressure', 'N/A')}")
            st.markdown(f"**Opportunity:** {fraud.get('opportunity', 'N/A')}")
            st.markdown(f"**Rationalization:** {fraud.get('rationalization', 'N/A')}")
        else:
            st.info("No fraud triangle analysis available.")

    st.divider()

    # XAI Narrative
    st.subheader("🤖 AI Analysis")
    if anomaly and anomaly.get('xai_narrative'):
        st.markdown(anomaly['xai_narrative'])
    elif case.get('xai_summary'):
        st.markdown(case['xai_summary'])

    st.divider()

    # SAR Report
    st.subheader("📋 Suspicious Activity Report")
    if case.get('sar_report'):
        with st.expander("View Full SAR Report"):
            st.markdown(case['sar_report'])
    else:
        st.info("SAR report not yet generated.")

    conn.close()


def show_sentinel_index():
    """Sentinel Index - searchable case database."""
    st.title("📊 Sentinel Index")
    st.caption("The world's first open database of potential prediction market insider trading")

    from src.data.database import get_connection, list_cases
    import pandas as pd

    conn = get_connection()

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_class = st.selectbox(
            "Classification",
            ["All", "INSIDER", "OSINT_EDGE", "FAST_REACTOR", "SPECULATOR"],
            key="index_class_filter"
        )
    with col2:
        filter_status = st.selectbox(
            "Status",
            ["All", "CONFIRMED", "DISPUTED", "UNDER_REVIEW"],
            key="index_status_filter"
        )
    with col3:
        search_query = st.text_input("Search markets", placeholder="e.g., tariff, bitcoin")

    cases = list_cases(
        conn,
        classification=filter_class if filter_class != "All" else None,
        status=filter_status if filter_status != "All" else None,
        limit=100
    )
    conn.close()

    if search_query:
        cases = [c for c in cases if search_query.lower() in c['market_name'].lower()]

    if not cases:
        st.info("No cases match your filters.")
        return

    # Convert to DataFrame for display
    df = pd.DataFrame(cases)
    df = df[['case_id', 'market_name', 'classification', 'bss_score', 'pes_score', 'consensus_score', 'status', 'created_at']]
    df.columns = ['Case ID', 'Market', 'Classification', 'BSS', 'PES', 'Consensus', 'Status', 'Created']

    # Style the dataframe
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Case ID": st.column_config.TextColumn(width="small"),
            "Market": st.column_config.TextColumn(width="large"),
            "Classification": st.column_config.TextColumn(width="small"),
            "BSS": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "PES": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            "Consensus": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
        }
    )

    # Export option
    col1, col2 = st.columns([1, 4])
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Export CSV",
            data=csv,
            file_name="sentinel_index.csv",
            mime="text/csv"
        )


def show_arena():
    """Sentinel Arena - human-in-the-loop voting."""
    st.title("⚖️ Sentinel Arena")
    st.caption("Help validate AI classifications through human consensus")

    from src.data.database import get_connection, list_cases, get_case, get_anomaly, insert_vote
    import json
    import uuid

    conn = get_connection()

    # Get cases under review
    cases = list_cases(conn, status="UNDER_REVIEW", limit=10)

    if not cases:
        st.success("🎉 All cases have been reviewed! Check back later for new cases.")
        conn.close()
        return

    st.info(f"📋 {len(cases)} cases awaiting review")

    # Show first case
    case = cases[0]
    anomaly = get_anomaly(conn, case['anomaly_event_id']) if case['anomaly_event_id'] else None

    st.divider()

    # Case summary
    st.markdown(f"### {case['market_name']}")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(get_classification_badge(case['classification']), unsafe_allow_html=True)
    with col2:
        st.metric("BSS Score", case['bss_score'])
    with col3:
        st.metric("PES Score", case['pes_score'])
    with col4:
        st.metric("Current Votes", case['vote_count'])

    # Evidence
    if anomaly and anomaly.get('xai_narrative'):
        with st.expander("📖 View AI Analysis", expanded=True):
            st.markdown(anomaly['xai_narrative'])

    st.divider()

    # Voting form
    st.subheader("Cast Your Vote")
    st.markdown(f"Do you agree with the **{case['classification']}** classification?")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✅ Agree", use_container_width=True, type="primary"):
            vote_id = str(uuid.uuid4())[:8]
            insert_vote(conn, {
                "vote_id": vote_id,
                "case_id": case['case_id'],
                "voter_id": "anonymous",
                "vote": "agree",
                "confidence": 4,
                "comment": None
            })
            conn.commit()
            st.success("Vote recorded! Thank you for your contribution.")
            st.rerun()

    with col2:
        if st.button("❌ Disagree", use_container_width=True):
            vote_id = str(uuid.uuid4())[:8]
            insert_vote(conn, {
                "vote_id": vote_id,
                "case_id": case['case_id'],
                "voter_id": "anonymous",
                "vote": "disagree",
                "confidence": 3,
                "comment": None
            })
            conn.commit()
            st.warning("Vote recorded. Your input helps improve our model.")
            st.rerun()

    with col3:
        if st.button("🤔 Uncertain", use_container_width=True):
            vote_id = str(uuid.uuid4())[:8]
            insert_vote(conn, {
                "vote_id": vote_id,
                "case_id": case['case_id'],
                "voter_id": "anonymous",
                "vote": "uncertain",
                "confidence": 2,
                "comment": None
            })
            conn.commit()
            st.info("Vote recorded. These edge cases help define classification boundaries.")
            st.rerun()

    conn.close()


def show_system_health():
    """System health and status."""
    st.title("🏥 System Health")
    import pandas as pd

    from src.data.database import get_connection, get_stats
    from src.classification.evaluation import compute_evaluation_metrics

    conn = get_connection()
    stats = get_stats(conn)
    eval_metrics = compute_evaluation_metrics(conn)
    conn.close()

    # Status indicators
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("✅ Database: Connected")
    with col2:
        st.success("✅ Mistral API: Ready")
    with col3:
        st.info("⏸️ Live Monitor: Paused")

    st.divider()

    # Database stats
    st.subheader("📊 Database Statistics")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Anomaly Events", stats['total_anomalies'])
    with col2:
        st.metric("OSINT Events", stats['total_osint_events'])
    with col3:
        st.metric("Wallet Profiles", stats['total_wallets'])
    with col4:
        st.metric("Indexed Cases", stats['total_cases'])
    with col5:
        st.metric("Evidence Packets", stats.get('total_evidence_packets', 0))

    # Classification breakdown
    st.subheader("📈 Classification Breakdown")
    if stats['cases_by_classification']:
        import plotly.express as px
        import pandas as pd

        df = pd.DataFrame([
            {"Classification": k, "Count": v}
            for k, v in stats['cases_by_classification'].items()
        ])

        colors = {
            "INSIDER": "#ff4b4b",
            "OSINT_EDGE": "#00cc66",
            "FAST_REACTOR": "#ffa500",
            "SPECULATOR": "#6c757d"
        }
        df['Color'] = df['Classification'].map(colors)

        fig = px.pie(df, values='Count', names='Classification', color='Classification',
                     color_discrete_map=colors)
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Status breakdown
    st.subheader("📋 Case Status")
    if stats['cases_by_status']:
        for status, count in stats['cases_by_status'].items():
            icon = {"CONFIRMED": "✅", "DISPUTED": "❌", "UNDER_REVIEW": "🔍"}.get(status, "⚪")
            st.text(f"{icon} {status}: {count}")

    st.divider()
    st.subheader("🧪 Evaluation Metrics")
    coverage = eval_metrics["coverage"]
    arena = eval_metrics["arena_consensus"]
    binary = eval_metrics["metrics"]
    cm_counts = eval_metrics["binary_confusion_matrix"]["counts"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Arena Consensus Accuracy", f"{(arena['consensus_accuracy'] or 0) * 100:.1f}%")
        st.caption(
            f"{arena['confirmed_cases']} confirmed / "
            f"{arena['confirmed_cases'] + arena['disputed_cases']} resolved"
        )
    with col2:
        fpr_text = "N/A" if binary["fpr"] is None else f"{binary['fpr'] * 100:.1f}%"
        fnr_text = "N/A" if binary["fnr"] is None else f"{binary['fnr'] * 100:.1f}%"
        st.metric("False Positive Rate", fpr_text)
        st.metric("False Negative Rate", fnr_text)
    with col3:
        acc_text = "N/A" if binary["accuracy"] is None else f"{binary['accuracy'] * 100:.1f}%"
        st.metric("Binary Accuracy", acc_text)
        st.caption(
            f"Evaluated: {coverage['evaluated_cases']} "
            f"(min_votes={coverage['min_votes']})"
        )

    cm_df = pd.DataFrame(
        [
            {"Actual": "POSITIVE", "Predicted POSITIVE": cm_counts["tp"], "Predicted NEGATIVE": cm_counts["fn"]},
            {"Actual": "NEGATIVE", "Predicted POSITIVE": cm_counts["fp"], "Predicted NEGATIVE": cm_counts["tn"]},
        ]
    )
    st.caption("Binary confusion matrix (positive class: INSIDER)")
    st.dataframe(cm_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
