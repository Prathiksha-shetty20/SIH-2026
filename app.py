import streamlit as st
import pandas as pd

from data import (
    build_schedule,
    SAMPLE_REPORT,
    SAMPLE_SHEET,
    SAMPLE_CHAT
)

from engine import (
    extract_text,
    extract_sheet,
    extract_chat,
    Linker,
    Store,
    process,
    history
)

def validate_progress(row, schedule):
    """
    Check actual progress against planned schedule dates.
    """

    activity_id = row.get("activity_id")

    if not activity_id:
        return []

    match = schedule[schedule["id"] == activity_id]

    if match.empty:
        return []

    activity = match.iloc[0]

    warnings = []

    actual_start = row.get("_ev", {}).get("date")
    actual_end = row.get("_ev", {}).get("date")

    event = row.get("event")

    planned_start = activity["planned_start"]
    planned_end = activity["planned_end"]

    if event == "start" and actual_start:
        if actual_start < planned_start:
            warnings.append(
                "Actual start is earlier than planned start."
            )

        if actual_start > planned_end:
            warnings.append(
                "Actual start is after planned end."
            )

    if event == "finish" and actual_end:
        if actual_end < planned_start:
            warnings.append(
                "Actual completion is earlier than planned start."
            )

        if actual_end > planned_end:
            warnings.append(
                "Actual completion is later than planned end."
            )

    return warnings


# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------

st.set_page_config(
    page_title="Planning-to-Execution Intelligence",
    page_icon="🏗️",
    layout="wide"
)


# ---------------------------------------------------------
# TITLE
# ---------------------------------------------------------

st.title(" Planning-to-Execution Progress Intelligence")


# ---------------------------------------------------------
# LOAD PROJECT DATA
# ---------------------------------------------------------

schedule = build_schedule()

if "store" not in st.session_state:
    st.session_state.store = Store(schedule)

if "results" not in st.session_state:
    st.session_state.results = []


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

st.sidebar.header("Navigation")

page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard",
        "Daily Report",
        "Discipline Sheet",
        "Supervisor Chat",
        "Planner Review",
        "Schedule",
        "Audit Trail"
    ]
)


# ---------------------------------------------------------
# HELPER FUNCTION
# ---------------------------------------------------------

def process_events(events, source_name):

    linker = Linker(schedule)

    rows = process(
        events,
        linker,
        st.session_state.store
    )

    for row in rows:

        validation_warnings = validate_progress(
            row,
            schedule
        )

        if validation_warnings:

            existing = row.get("warnings", "")

            if existing:
                row["warnings"] = (
                    existing
                    + "; "
                    + "; ".join(validation_warnings)
                )
            else:
                row["warnings"] = "; ".join(
                    validation_warnings
                )

    st.session_state.results.extend(rows)

    return rows


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":

    st.header("Project Progress Dashboard")

    results = st.session_state.results

    # ==========================================
    # SUMMARY METRICS
    # ==========================================

    if results:

        total = len(results)

        auto = sum(
            r["status"] == "auto"
            for r in results
        )

        review = sum(
            r["status"] == "review"
            for r in results
        )

        unmatched = sum(
            r["status"] == "unmatched"
            for r in results
        )

    else:

        total = 0
        auto = 0
        review = 0
        unmatched = 0


    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Events Processed",
        total
    )

    col2.metric(
        "Auto Linked",
        auto
    )

    col3.metric(
        "Planner Review",
        review
    )

    col4.metric(
    "Unmatched",
    unmatched
    )

# ==========================================
# PROCESSING STATUS
# ==========================================

    if total > 0:

        st.subheader("🔎 Processing Status")

        status_df = pd.DataFrame({
            "Status": [
                "Auto Linked",
                "Planner Review",
                "Unmatched"
            ],
            "Count": [
                auto,
                review,
                unmatched
            ]
            })

        st.bar_chart(
        status_df.set_index("Status")
    )

    st.divider()


# ==========================================
# PROGRESS BY DISCIPLINE
# ==========================================

    st.subheader(" Progress by Discipline")

    discipline_rows = []

    for discipline in schedule["discipline"].unique():

        discipline_activities = schedule[
            schedule["discipline"] == discipline
        ]

        total_activities = len(discipline_activities)

        completed_or_started = 0
        progress_values = []

        for _, activity in discipline_activities.iterrows():

            activity_id = activity["id"]

            if activity_id in st.session_state.store.actual:

                state = st.session_state.store.actual[activity_id]

                pct = state.get("pct")

                if pct is not None:
                    progress_values.append(pct)

                    if pct > 0:
                        completed_or_started += 1

        if progress_values:
            avg_progress = sum(progress_values) / len(progress_values)
        else:
            avg_progress = 0

        discipline_rows.append({

            "Discipline": discipline,

            "Planned Activities": total_activities,

            "Activities with Progress": completed_or_started,

            "Average Progress": f"{avg_progress:.0f}%"

        })


    discipline_df = pd.DataFrame(discipline_rows)

    st.dataframe(
        discipline_df,
        use_container_width=True,
        hide_index=True
    )


    st.divider()    

    # ==========================================
    # CURRENT ACTUAL PROGRESS
    # ==========================================

    st.subheader("Current Actual Progress")

    state_rows = []

    for activity_id, state in st.session_state.store.actual.items():

        if (
            state["start"] is not None
            or state["end"] is not None
            or state["pct"] is not None
        ):

            activity = schedule[
                schedule["id"] == activity_id
            ].iloc[0]

            state_rows.append({

                "Activity ID": activity_id,

                "Discipline": activity["discipline"],

                "Activity": activity["name"],

                "Planned Start": activity["planned_start"],

                "Planned End": activity["planned_end"],

                "Actual Start": state["start"],

                "Actual End": state["end"],

                "Progress": state["pct"]

            })


    if state_rows:

        df = pd.DataFrame(state_rows)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No actual progress has been processed yet. "
            "Use one of the input pages from the sidebar."
        )


    st.divider()


    # ==========================================
    # SCHEDULE VALIDATION ALERTS
    # ==========================================

    st.subheader(" Schedule Validation Alerts")

    alerts = []

    for row in st.session_state.results:

        warnings = row.get("warnings", "")

        if warnings:

            alerts.append({

                "Activity ID": row.get(
                    "activity_id",
                    "Unmatched"
                ),

                "Field Report": row.get(
                    "text",
                    ""
                ),

                "Warning": warnings

            })


    if alerts:

        alert_df = pd.DataFrame(alerts)

        st.dataframe(
            alert_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.success(
            "No schedule validation issues detected."
        )


# =========================================================
# DAILY REPORT
# =========================================================

elif page == "Daily Report":

    st.header("Daily Progress Report")

    st.write(
        "Extract actual progress events from a daily field report."
    )

    report_text = st.text_area(
        "Daily Report",
        value=SAMPLE_REPORT,
        height=300
    )


    if st.button(
        "🚀 Process Daily Report",
        type="primary"
    ):

        events = extract_text(
            report_text,
            doc="daily_report"
        )

        rows = process_events(
            events,
            "daily_report"
        )

        st.success(
            f"{len(rows)} progress events extracted and processed."
        )

        st.subheader("Extracted Events")

        display_rows = []

        for r in rows:

            display_rows.append({
                "Activity": r["text"],
                "Event": r["event"],
                "Date": r["date"],
                "Matched Activity": r["activity_id"],
                "Confidence": f'{r["confidence"]:.0%}',
                "Decision": r["status"],
                "Why": r.get("reason", ""),
                "Warning": r.get("warnings", "")
            })

        st.dataframe(
            pd.DataFrame(display_rows),
            use_container_width=True
        )


# =========================================================
# DISCIPLINE SHEET
# =========================================================

elif page == "Discipline Sheet":

    st.header("Discipline Progress Sheet")

    st.write(
        "Process structured discipline-level progress information."
    )


    st.subheader("Sample Input")

    st.dataframe(
        SAMPLE_SHEET,
        use_container_width=True
    )


    if st.button(
        "🚀 Process Discipline Sheet",
        type="primary"
    ):

        events = extract_sheet(
            SAMPLE_SHEET,
            doc="discipline_sheet"
        )

        rows = process_events(
            events,
            "discipline_sheet"
        )

        st.success(
            f"{len(rows)} spreadsheet events processed."
        )

        display_rows = []

        for r in rows:

            display_rows.append({
                "Activity": r["text"],
                "Event": r["event"],
                "Tag": r["_ev"].get("tag"),
                "Matched Activity": r["activity_id"],
                "Confidence": f'{r["confidence"]:.0%}',
                "Decision": r["status"],
                "Why": r.get("reason", ""),
                "Warning": r.get("warnings", "")
            })

        st.dataframe(
            pd.DataFrame(display_rows),
            use_container_width=True
        )


# =========================================================
# SUPERVISOR CHAT
# =========================================================

elif page == "Supervisor Chat":

    st.header(" Supervisor Progress Capture")

    st.write(
        "Simulate a low-friction conversational progress update "
        "from a site supervisor."
    )


    chat_text = st.text_area(
        "Supervisor Updates",
        value=SAMPLE_CHAT,
        height=250
    )


    if st.button(
        "🚀 Process Supervisor Updates",
        type="primary"
    ):

        events = extract_chat(
            chat_text,
            doc="supervisor_chat"
        )

        rows = process_events(
            events,
            "supervisor_chat"
        )

        st.success(
            f"{len(rows)} supervisor updates processed."
        )

        display_rows = []

        for r in rows:

            display_rows.append({
                "Supervisor Update": r["text"],
                "Event": r["event"],
                "Tag": r["_ev"].get("tag"),
                "Matched Activity": r["activity_id"],
                "Confidence": f'{r["confidence"]:.0%}',
                "Decision": r["status"],
                "Why": r.get("reason", ""),
                "Warning": r.get("warnings", "")
            })

        st.dataframe(
            pd.DataFrame(display_rows),
            use_container_width=True
        )

# =========================================================
# PLANNER REVIEW
# =========================================================

elif page == "Planner Review":

    st.header("Planner Review")

    st.write(
        "Review low-confidence activity matches before updating "
        "the project schedule."
    )

    review_rows = [
        r for r in st.session_state.results
        if r["status"] == "review"
    ]

    if not review_rows:

        st.success(
            "No activities currently require planner review."
        )

    else:

        st.info(
            f"{len(review_rows)} activity/event(s) require planner confirmation."
        )

        for idx, row in enumerate(review_rows):

            st.divider()

            st.subheader(
                f"Review Item {idx + 1}"
            )

            st.write("**Field Report:**")
            st.write(row["text"])

            col1, col2, col3 = st.columns(3)

            col1.write(
                f"**Discipline:** "
                f"{row['_ev'].get('discipline', 'Unknown')}"
            )

            col2.write(
                f"**Event:** {row['event']}"
            )

            col3.write(
                f"**Initial Confidence:** "
                f"{row['confidence']:.0%}"
            )

            st.info(
                f"Why this needs review: {row.get('reason', 'No explanation available.')}"
            )
            st.write("**Suggested Schedule Activities:**")

            candidates = row.get("cands", [])

            candidate_labels = []

            for activity_id, score in candidates:

                match = schedule[
                    schedule["id"] == activity_id
                ]

                if not match.empty:

                    activity = match.iloc[0]

                    label = (
                        f"{activity_id} — "
                        f"{activity['name']} | "
                        f"{activity['discipline']} | "
                        f"{activity['planned_start']} → "
                        f"{activity['planned_end']} | "
                        f"Match: {score:.0%}"
                        )

                    candidate_labels.append(
                        (label, activity_id, score)
                    )

            if candidate_labels:

                labels = [
                    x[0]
                    for x in candidate_labels
                ]

                selected_label = st.selectbox(
                    "Select the correct schedule activity",
                    labels,
                    key=f"review_select_{idx}"
                )

                selected = next(
                    x for x in candidate_labels
                    if x[0] == selected_label
                )

                selected_activity_id = selected[1]
                selected_confidence = selected[2]

                if st.button(
                    "✅ Confirm Activity",
                    key=f"confirm_{idx}"
                ):

                    warnings = st.session_state.store.apply(
                        row["_ev"],
                        selected_activity_id,
                        selected_confidence,
                        "planner_confirmed"
                    )

                    row["activity_id"] = selected_activity_id
                    row["confidence"] = selected_confidence
                    row["status"] = "planner_confirmed"
                    row["reason"] = "confirmed by planner"
                    row["warnings"] = "; ".join(warnings)

                    st.success(
                        f"Activity confirmed: {selected_activity_id}"
                    )

                    if warnings:

                        st.warning(
                            "Validation warning: "
                            + "; ".join(warnings)
                        )

                    st.rerun()

            else:

                st.warning(
                    "No suitable schedule candidates were generated."
                )


# =========================================================
# SCHEDULE
# =========================================================

elif page == "Schedule":

    st.header(" L5/L6 Project Schedule")

    st.write(
        "Synthetic Primavera-style schedule used by the prototype."
    )

    st.dataframe(
        schedule,
        use_container_width=True
    )


# =========================================================
# AUDIT TRAIL
# =========================================================

elif page == "Audit Trail":

    st.header(" Audit Trail")

    audit_records = st.session_state.store.audit

    if audit_records:

        audit_df = pd.DataFrame(audit_records)

        audit_df = audit_df.rename(columns={
            "time": "Timestamp",
            "activity_id": "Activity ID",
            "event": "Event",
            "date": "Event Date",
            "confidence": "Confidence",
            "status": "Decision",
            "source": "Source",
            "text": "Field Input",
            "warnings": "Warnings"
        })

        audit_df["Confidence"] = audit_df["Confidence"].apply(
            lambda x: f"{x:.0%}"
        )

        audit_df = audit_df[
            [
                "Timestamp",
                "Source",
                "Field Input",
                "Activity ID",
                "Event",
                "Event Date",
                "Confidence",
                "Decision",
                "Warnings"
            ]
        ]

        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info(
            "No audit records yet. Process a report, "
            "spreadsheet or supervisor update first."
        )