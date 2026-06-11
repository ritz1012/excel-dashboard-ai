import streamlit as st
import pandas as pd
import plotly.express as px
from ai_agent import generate_dashboard_plan

st.set_page_config(page_title="AI Dashboard Generator")

st.title("AI Dashboard Generator")

uploaded_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

if uploaded_file:

    # Read Excel
    df = pd.read_excel(uploaded_file)

    # Excel sheets often mix text and dates in one column, which
    # breaks sorting and display. Coerce mostly-date columns to
    # datetime and make remaining mixed columns plain strings.
    for col in df.columns:
        if df[col].dtype == object:
            converted = pd.to_datetime(df[col], errors="coerce")
            if converted.notna().sum() >= df[col].notna().sum() * 0.8:
                df[col] = converted
            else:
                df[col] = df[col].astype(str)

    # Data Preview
    st.subheader("Data Preview")
    st.dataframe(df)

    st.success(
        f"Loaded {len(df)} rows and {len(df.columns)} columns"
    )

    # Dataset Information
    st.subheader("Dataset Information")

    st.write(f"Rows: {df.shape[0]}")
    st.write(f"Columns: {df.shape[1]}")

    st.write("Column Names:")
    st.write(df.columns.tolist())
    st.divider()

def render_kpis(df, kpis):

    valid_kpis = [
        k for k in kpis
        if isinstance(k, dict) and k.get("column") in df.columns
    ][:4]

    if not valid_kpis:
        return

    cols = st.columns(len(valid_kpis))

    for i, kpi in enumerate(valid_kpis):

        column = kpi["column"]
        agg = kpi.get("agg", "sum")
        label = kpi.get("label", column)
        series = df[column]

        if agg == "count":
            value = series.count()
        elif pd.api.types.is_numeric_dtype(series):
            value = getattr(series, agg, series.sum)()
        else:
            value = series.nunique()
            label = f"Unique {column}"

        if isinstance(value, float):
            display = f"{value:,.1f}"
        else:
            display = f"{value:,}"

        cols[i].metric(label=label, value=display)


def render_chart(df, chart):

    chart_type = chart.get("type")
    x = chart.get("x")
    y = chart.get("y")
    title = chart.get("title", "")

    if x not in df.columns:
        return

    if chart_type == "histogram":
        fig = px.histogram(df, x=x, title=title)

    elif y not in df.columns:
        return

    elif chart_type == "scatter":
        fig = px.scatter(df, x=x, y=y, title=title)

    elif chart_type in ("bar", "line", "pie"):

        plot_df = df[[x, y]].copy()

        # Excel columns often mix strings and datetimes, which
        # breaks sorting. Coerce to datetime when mostly dates,
        # otherwise fall back to plain strings.
        if not pd.api.types.is_numeric_dtype(plot_df[x]) and \
                not pd.api.types.is_datetime64_any_dtype(plot_df[x]):

            converted = pd.to_datetime(plot_df[x], errors="coerce")

            if converted.notna().sum() >= plot_df[x].notna().sum() * 0.8:
                plot_df[x] = converted
            else:
                plot_df[x] = plot_df[x].astype(str)

        # Aggregate so each x value appears once
        if pd.api.types.is_numeric_dtype(plot_df[y]):
            grouped = plot_df.groupby(x)[y].sum().reset_index()
        else:
            grouped = plot_df.groupby(x)[y].count().reset_index()

        if chart_type == "bar":
            fig = px.bar(grouped, x=x, y=y, title=title)
        elif chart_type == "line":
            grouped = grouped.sort_values(x)
            fig = px.line(grouped, x=x, y=y, title=title)
        else:
            fig = px.pie(grouped, names=x, values=y, title=title)

    else:
        return

    st.plotly_chart(fig, use_container_width=True)


def render_table(df, table):

    if not isinstance(table, dict):
        return

    columns = [
        c for c in table.get("columns", [])
        if c in df.columns
    ]

    if not columns:
        return

    table_df = df[columns]

    sort_by = table.get("sort_by")
    if sort_by in columns:
        table_df = table_df.sort_values(
            sort_by,
            ascending=table.get("ascending", True)
        )

    st.subheader(table.get("title", "Table Data"))
    st.dataframe(table_df, use_container_width=True)


def render_ai_dashboard(df, plan):

    st.header(plan.get("title", "AI Dashboard"))

    render_kpis(df, plan.get("kpis", []))

    charts = plan.get("charts", [])
    for i in range(0, len(charts), 2):

        row = st.columns(2)

        for j, chart in enumerate(charts[i:i + 2]):
            with row[j]:
                render_chart(df, chart)

    render_table(df, plan.get("table"))

    insight = plan.get("insight")
    if insight:
        st.subheader("AI Insight")
        st.info(insight)


st.header("AI Dashboard Assistant")

EXAMPLE_PROMPTS = [
    "Create an executive summary dashboard with overall progress and key metrics",
    "Show employee workload and who is overloaded with tasks",
    "Show project progress over time and highlight projects falling behind",
    "Identify delayed or at-risk tasks and who they are assigned to",
    "Compare projects by effort required and completion status",
    "Show task distribution by status with a timeline of start dates",
]

selected_example = st.selectbox(
    "Try an example prompt",
    ["Write my own..."] + EXAMPLE_PROMPTS,
)

user_prompt = st.text_area(
    "Describe the dashboard you want",
    value="" if selected_example == "Write my own..." else selected_example,
    placeholder="""
Example:
Show employee workload
Show project progress
Create executive summary
Identify delayed tasks
"""
)

if st.button("Generate Dashboard With AI"):

    if not uploaded_file:
        st.warning("Please upload an Excel file first.")

    elif not user_prompt.strip():
        st.warning("Please describe the dashboard you want.")

    else:

        with st.spinner("AI is analyzing your data..."):
            result = generate_dashboard_plan(df, user_prompt)

        render_ai_dashboard(df, result)