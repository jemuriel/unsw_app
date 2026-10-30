
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="University Enrolment Intelligence",
    page_icon="🎓",
    layout="wide"
)

# -----------------------------
# DATA
# -----------------------------
def load_and_clean()-> pd.DataFrame:

    # Load all sheets as DataFrames

    file_path = r"C:\Users\jemur\Dropbox\UNSW_26\unsw_app\VIC_Uni_Enrols_2019-2021_Exercise 1.xlsx"

    dfs = pd.read_excel(file_path, sheet_name=None)
    field, vic_df, course, competitors = dfs.values()

    # vic_df = vic_df.head(10000)

    # Change domestic indicatro if 'not provided'
    vic_df.loc[
        (vic_df['overseas_domestic_indicator'] == 'Not provided') &
        (vic_df['perm_home_res'] != 'Australia'),
        'overseas_domestic_indicator'
    ] = 'Overseas Students'

    # TODO Change SES_2016_SA1 status if 'Unknown'

    # Left join

    # Validate reference table keos
    assert course["level_of_course"].is_unique
    assert competitors["Institution"].is_unique

    # Join 1: Course classification
    df_joined = vic_df.merge(
        course,
        on="level_of_course",
        how="left",
        validate="many_to_one",
        indicator="course_match"
    )

    # Join 2: Competitor classification
    df_joined = df_joined.merge(
        competitors,
        left_on="institution",
        right_on="Institution",
        how="left",
        validate="many_to_one",
        indicator="competitor_match"
    )

    # Checs unmatched records ----------------------------
    print("Course joins:")
    print(df_joined["course_match"].value_counts())

    print('-'*50)
    print("\nCompetitor joins:")
    print(df_joined["competitor_match"].value_counts())

    # Reconciliation
    assert len(df_joined) == len(vic_df)
    assert df_joined["enrolments"].sum() == vic_df["enrolments"].sum()

    # competitor flag
    df_joined["is_key_competitor"] = (
        df_joined["Key UNSW Competitor"].eq("Y")
    )

    print("\nmll join reconciliation checks passed.")

    # Check missing values per colunm
    missing = df_joined.isna().sum()

    print(missing[missing > 0])

    # Check row count and enrolment reconciliation
    print('-'*50)
    print("\nOriginal rows:", len(vic_df))
    print("Joined rows:", len(df_joined))

    print('-'*50)
    print("\nOriginal enrolments:", vic_df["enrolments"].sum())
    print("Joined enrolments:", df_joined["enrolments"].sum())

    # Missing values --------------------------------------
    # Check empty strings and whitespace
    empty_strings = df_joined.select_dtypes(include="object").apply(
        lambda col: col.astype("string").str.strip().eq("").sum()
    )

    print('-'*50)
    print("\nEmpty strings:")
    print(empty_strings[empty_strings > 0])

    # Duplicated records -----------------------------------
    # Exact duplicates across all columns
    duplicates = df_joined.duplicated().sum()

    print("Exact duplicate rows:", duplicates)

    # Display if any
    if duplicates > 0:
        display(df_joined[df.duplicated(keep=False)].head(10))

    # invalid enrollments -----------------------------------

    # Convert enrolments to numeric
    enrolments = pd.to_numeric(
        df_joined["enrolments"],
        errors="coerce"
    )

    print("Missing/non-numeric:", enrolments.isna().sum())
    print("Negative values:", (enrolments < 0).sum())
    print("Zero values:", (enrolments == 0).sum())
    print("Non-integer values:",
        (enrolments.dropna() % 1 != 0).sum())

    print("\nEnrolment summary:")
    print(enrolments.describe())

    # Coverage across years ----------------------------
    # Inspect actual column names
    print('-'*50)
    print(df_joined.columns.tolist())

    # Check institution-year coverage
    coverage = pd.crosstab(
        df_joined["institution"],
        df_joined["ref_year"]
    )

    print(coverage.to_string())

    print('-'*50)
    print("\nYears available:")
    print(sorted(df_joined["ref_year"].dropna().unique()))

    return df_joined

df = load_and_clean()

# -----------------------------
# SIDEBAR
# -----------------------------

st.sidebar.title("UNSW")
st.sidebar.caption("Planning & Performance")

section = st.sidebar.radio(
    "Dashboard",
    [
        "Data Validation",
        "Market Overview",
        "Competition",
        "Portfolio",
        "Student Demand"
    ]
)

st.sidebar.divider()
st.sidebar.subheader("Filters")

# 1. Competitor filter
competitors_only = st.sidebar.checkbox(
    "Show competitors only",
    value=False
)

df_filtered = df.copy()

if competitors_only:
    df_filtered = df_filtered[
        df_filtered["is_key_competitor"]
    ]

# 2. University filter
available_institutions = sorted(
    df_filtered["institution"].dropna().unique()
)

institutions = st.sidebar.multiselect(
    "Universities",
    options=available_institutions,
    default=available_institutions
)

# 3. Year filter
years = st.sidebar.slider(
    "Reporting years",
    min_value=2019,
    max_value=2021,
    value=(2019, 2021)
)

# 4. Apply all filters
filtered = df_filtered[
    df_filtered["institution"].isin(institutions)
    & df_filtered["ref_year"].between(*years)
].copy()

# -----------------------------
# THEME 1: MARKET OVERVIEW
# -----------------------------

if section == "Data Validation":
    st.subheader("Valid unknowns and missing information")

    data = [
        ["gender", "Indeterminate/Intersex/Unspecified", 887, 1020,
        "Valid combined category; do not recode entirely to Unknown."],
        ["perm_home_res", "Overseas Country not known", 471, 1088,
        "Overseas residence is known; country is unknown."],
        ["perm_home_res", "Unknown-Overseas", 278, 498,
        "Preserve separately until equivalence with other unknown labels is confirmed."],
        ["perm_home_res", "Not provided", 785, 1248,
        "Missing residence information."],
        ["country_of_birth", "Overseas Country not known", 227, 323,
        "Partial information; not an invalid country entry."],
        ["country_of_birth", "Not provided", 132, 172,
        "Missing birth-country information."],
        ["basis_for_admission_1", "Not provided", 3449, 8188,
        "Missing admission information; assess within the commencing population."],
        ["overseas_domestic_indicator", "Not provided", 1, 1,
        "Retain as Unknown; do not infer from birthplace or residence."],
        ["SES_2016_SA1", "Unknown", 288, 315,
        "Unknown socioeconomic classification."],
        ["SES_2016_SA1", "Out of Scope", 29654, 114470,
        "Outside the classification population; keep distinct from Unknown."],       
    ]

    table = pd.DataFrame(
        data,
        columns=["Column", "Value", "Records", "Enrolments", "Treatment"],
    )
    table.insert(
        3, "Records (%)",
        table["Records"].div(236_657).mul(100).map(lambda x: f"{x:.4f}%")
    )

    st.dataframe(table, hide_index=True)
    st.caption(
        "Percentages use 236,657 source records. Enrolments are weighted counts. "
        "Categories can overlap across columns; do not sum them."
    )

elif section == "Market Overview":

    st.title("Market Overview")
    st.caption(
        "Victorian university enrolment trends | 2019–2021"
    )

    yearly = (
        filtered.groupby("ref_year", as_index=False)
        ["enrolments"].sum()
    )

    if yearly.empty:
        st.warning("No records match the filters.")
        st.stop()

    start = yearly.iloc[0]["enrolments"]
    end = yearly.iloc[-1]["enrolments"]

    growth = (
        (end / start - 1) * 100
        if start > 0 and len(yearly) > 1
        else None
    )

    # Domestic / international categories
    origin_col = "overseas_domestic_indicator"

    origin = (
        filtered.groupby(
            ["ref_year", origin_col],
            as_index=False
        )["enrolments"].sum()
    )

    # Inspect actual category labels
    st.sidebar.caption(
        "Origin categories: "
        + ", ".join(
            map(str, sorted(df[origin_col].dropna().unique()))
        )
    )

    # -----------------------------
    # KPI CARDS
    # -----------------------------

    k1, k2, k3, k4 = st.columns(4)

    k1.metric(
        "Total enrolments",
        f"{filtered['enrolments'].sum():,.0f}"
    )

    k2.metric(
        "Period growth",
        f"{growth:+.1f}%" if growth is not None else "N/A"
    )

    # Use the actual category values from the workbook
    origin_values = {
        str(v).strip().lower(): v
        for v in df[origin_col].dropna().unique()
    }

    def origin_growth(keyword):
        matches = [
            v for label, v in origin_values.items()
            if label == keyword or (keyword == "overseas" and label == "overseas students") or (keyword == "domestic" and label == "domestic students")
        ]

        if not matches or len(yearly) < 2:
            return None

        subset = origin[origin[origin_col].isin(matches)]
        totals = subset.groupby("ref_year")["enrolments"].sum()

        if years[0] not in totals or years[1] not in totals:
            return None

        baseline = totals.loc[years[0]]
        if baseline == 0:
            return None

        return (totals.loc[years[1]] / baseline - 1) * 100

    domestic_growth = origin_growth("domestic")
    international_growth = origin_growth("overseas")

    k3.metric(
        "Domestic growth",
        f"{domestic_growth:+.1f}%"
        if domestic_growth is not None else "N/A"
    )

    k4.metric(
        "International growth",
        f"{international_growth:+.1f}%"
        if international_growth is not None else "N/A"
    )

    st.divider()

    # -----------------------------
    # CHART 1: TOTAL ENROLMENTS
    # -----------------------------

    # st.subheader("1. Total enrolment trends")

    fig_total = px.bar(
        yearly,
        x="ref_year",
        y="enrolments",
        text="enrolments",
        labels={
            "ref_year": "Year",
            "enrolments": "Enrolments"
        }
    )

    fig_total.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside"
    )

    fig_total.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=sorted(yearly["ref_year"].unique())
        ),
        yaxis=dict(rangemode="tozero"),
        showlegend=False
    )

    # st.plotly_chart(fig_total, use_container_width=True)

    # -----------------------------
    # CHART 2: STUDENT ORIGIN
    # -----------------------------

    # st.subheader("2. Domestic vs international")

    fig_origin = px.line(
        origin,
        x="ref_year",
        y="enrolments",
        color=origin_col,
        markers=True,
        labels={
            "ref_year": "Year",
            "enrolments": "Enrolments",
            origin_col: "Student origin"
        }
    )

    fig_origin.update_layout(
        xaxis=dict(
            tickmode="array",
            tickvals=sorted(yearly["ref_year"].unique())
        )
    )

    # st.plotly_chart(fig_origin, use_container_width=True)

    
    # -----------------------------
    # CHART 3: COMPOSITION (100%)
    # -----------------------------

    # Replace the original fig_mix with percentage composition
    origin_pct = origin.copy()

    origin_pct["percentage"] = (
        origin_pct["enrolments"]
        / origin_pct.groupby("ref_year")["enrolments"].transform("sum")
        * 100
    )

    fig_mix = px.bar(
        origin_pct,
        x="ref_year",
        y="percentage",
        color=origin_col,
        barmode="stack",
        labels={
            "ref_year": "Year",
            "percentage": "Share (%)",
            origin_col: "Student origin"
        }
    )

    fig_mix.update_yaxes(range=[0, 100], ticksuffix="%")

    # -----------------------------
    # CONSISTENT CHART FORMATTING
    # -----------------------------

    for fig in [fig_total, fig_origin, fig_mix]:
        fig.update_layout(
            height=350,
            margin=dict(l=10, r=10, t=45, b=30),
            font=dict(size=11),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=10)
            )
        )

    # -----------------------------
    # THREE CHARTS IN ONE ROW
    # -----------------------------

    col1, col2, col3 = st.columns(3, gap="medium")

    with col1:
        st.markdown("**1. Total enrolment trends**")
        st.plotly_chart(fig_total, use_container_width=True)

    with col2:
        st.markdown("**2. Domestic vs international**")
        st.plotly_chart(fig_origin, use_container_width=True)

    with col3:
        st.markdown("**3. Student composition (%)**")
        st.plotly_chart(fig_mix, use_container_width=True)

    

    # ============================================
    # INTERNATIONAL MARKETS - CHARTS 4, 5 AND 6
    # ============================================

    st.divider()
    st.subheader("International Markets")

    start_year, end_year = years

    if start_year == end_year:
        st.info(
            "Select at least two reporting years to analyse "
            "international market growth."
        )

    else:

        # ----------------------------------------
        # 1. Prepare international student data
        # ----------------------------------------

        international = filtered[
            filtered["overseas_domestic_indicator"]
            .astype("string")
            .str.strip()
            .str.casefold()
            .isin(["overseas", "overseas students"])
        ].copy()
        
        international = international[
            international["perm_home_res"].astype("string").str.strip().str.casefold().ne("australia").fillna(False)
        ]

        international["country"] = (
            international["perm_home_res"]
            .astype("string")
            .str.strip()
        )

        # # Get unique countries
        # unique_countries = international['country'].unique()

        # # Display in Streamlit
        # st.write(unique_countries)

        international = international[
            international["country"].notna()
            & ~international["country"].str.casefold().isin([
                "",
                "unknown",
                "not provided",
                "not stated",
                "not known"
            ])
        ].copy()

        if international.empty:
            st.warning(
                "No international enrolments match the selected filters."
            )

        else:

            # ----------------------------------------
            # 2. Country-level growth metrics
            # ----------------------------------------

            country_year = (
                international.groupby(
                    ["country", "ref_year"]
                )["enrolments"]
                .sum()
                .unstack(fill_value=0)
            )

            country_year = country_year.reindex(
                columns=[start_year, end_year],
                fill_value=0
            )

            country_year["growth_abs"] = (
                country_year[end_year]
                - country_year[start_year]
            )

            country_year["growth_pct"] = (
                country_year["growth_abs"]
                / country_year[start_year].replace(0, float("nan"))
                * 100
            )

            total_latest = country_year[end_year].sum()

            country_year["share_pct"] = (
                country_year[end_year] / total_latest * 100
                if total_latest > 0 else 0
            )

            # ----------------------------------------
            # 3. Calculate cumulative enrolment share
            # ----------------------------------------

            country_ranked = country_year.sort_values(
                end_year, ascending=False
            ).copy()

            country_ranked["cumulative_share"] = (
                country_ranked["share_pct"].cumsum()
            )

            # Include the country that crosses 80%
            previous_cumulative = (
                country_ranked["cumulative_share"]
                - country_ranked["share_pct"]
            )

            top_80_countries = country_ranked.index[
                previous_cumulative < 80
            ].tolist()

            # ----------------------------------------
            # 4. Interactive toggle
            # ----------------------------------------

            show_top_80 = st.toggle(
                "Show countries representing ~80% of international enrolments",
                value=False,
                help=(
                    "Ranks source countries by enrolments in the latest selected "
                    "year and includes countries until their cumulative share "
                    "reaches at least 80%. Growing and declining countries "
                    "are both eligible."
                ),
                key="international_enrolment_80"
            )

            if show_top_80:
                selected_countries = top_80_countries
            else:
                selected_countries = country_year.index.tolist()

            country_data = country_year.loc[
                selected_countries
            ].copy()

            # ========================================
            # CHART 4 - INTERNATIONAL MARKET POSITIONING
            # ========================================

            bubble_data = (
                country_data.reset_index()
                .rename(columns={
                    end_year: "latest_enrolments"
                })
            )

            # Growth rate is undefined for a zero baseline.
            # Exclude these from the bubble chart rather
            # than displaying an artificial 0% growth.

            bubble_data = bubble_data[
                bubble_data["growth_pct"].notna()
                & (bubble_data["latest_enrolments"] > 0)
            ].copy()

            bubble_data["growth_status"] = bubble_data[
                "growth_abs"
            ].apply(
                lambda x: "Growing" if x > 0
                else "Declining" if x < 0
                else "Stable"
            )

            # Fixed strategic boundary: 5% of international enrolments.
            share_threshold = 5.0

            # Keep the horizontal scale stable when the 80% toggle changes.
            eligible_countries = country_year.loc[
                country_year["growth_pct"].notna()
                & (country_year[end_year] > 0)
            ]

            fig_positioning = px.scatter(
                bubble_data,
                x="share_pct",
                y="growth_pct",
                size="latest_enrolments",
                color="growth_status",
                hover_name="country",
                size_max=42,
                color_discrete_map={
                    "Growing": "#28A879",
                    "Declining": "#E36A63",
                    "Stable": "#AAB4BF",
                },
                hover_data={
                    "share_pct": ":.2f",
                    "growth_pct": ":+.1f",
                    "latest_enrolments": ":,",
                    "growth_abs": ":+,.0f",
                },
                labels={
                    "share_pct": f"International enrolment share in {end_year} (%)",
                    "growth_pct": f"Enrolment growth {start_year}–{end_year} (%)",
                    "latest_enrolments": f"Enrolments in {end_year}",
                    "growth_abs": "Absolute change",
                    "growth_status": "Market trend",
                },
            )

            if not bubble_data.empty:
                # Use a shared scale for both filter settings to avoid
                # reclassifying countries merely because some are hidden.
                x_max = max(
                    float(eligible_countries["share_pct"].max()) * 1.18,
                    share_threshold * 2.5,
                    1.0,
                )
                y_min = min(float(eligible_countries["growth_pct"].min()), 0) - 12
                y_max = 100.0
                # Keep a minimum vertical span for readable labels.
                y_min = min(y_min, -12)

                quadrants = [
                    (0, share_threshold, 0, y_max, "rgba(85,134,213,0.07)"),
                    (share_threshold, x_max, 0, y_max, "rgba(40,168,121,0.07)"),
                    (0, share_threshold, y_min, 0, "rgba(213,160,33,0.07)"),
                    (share_threshold, x_max, y_min, 0, "rgba(227,106,99,0.07)"),
                ]
                for x0, x1, y0, y1, colour in quadrants:
                    fig_positioning.add_shape(
                        type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                        fillcolor=colour, line_width=0, layer="below",
                    )

                fig_positioning.add_hline(
                    y=0, line_dash="dash", line_color="#8793A3", line_width=1.2
                )
                fig_positioning.add_vline(
                    x=share_threshold, line_dash="dash",
                    line_color="#8793A3", line_width=1.2,
                )

                # Paper-relative labels stay readable even if one quadrant
                # is narrow or there are extreme growth-rate outliers.
                for title, x_pos, y_pos, anchor in [
                    ("Emerging growth", 0.02, 0.97, "left"),
                    ("Established growth", 0.98, 0.97, "right"),
                    ("Smaller declining", 0.02, 0.03, "left"),
                    ("Major markets at risk", 0.98, 0.03, "right"),
                ]:
                    fig_positioning.add_annotation(
                        xref="paper", yref="paper", x=x_pos, y=y_pos,
                        text=f"<b>{title}</b>", showarrow=False,
                        xanchor=anchor, yanchor="middle",
                        font=dict(size=10, color="#8190A3"),
                        bgcolor="rgba(255,255,255,0.72)",
                        borderpad=3,
                    )

                fig_positioning.update_xaxes(range=[0, x_max], ticksuffix="%")
                fig_positioning.update_yaxes(range=[y_min, y_max], ticksuffix="%")
            else:
                fig_positioning.update_xaxes(ticksuffix="%", rangemode="tozero")
                fig_positioning.update_yaxes(range=[-12, 100], ticksuffix="%")

            fig_positioning.update_traces(
                marker=dict(opacity=0.85, line=dict(width=1, color="white"))
            )
            fig_positioning.update_layout(
                hovermode="closest",
                plot_bgcolor="rgba(0,0,0,0)",
            )

            # ========================================
            # CHART 5 - COUNTRY x FIELD GROWTH HEATMAP
            # ========================================

            field_data = international[
                international["country"].isin(
                    selected_countries
                )
            ].copy()

            field_year = (
                field_data.groupby(
                    ["country", "broad_foe", "ref_year"]
                )["enrolments"]
                .sum()
                .unstack(fill_value=0)
            )

            field_year = field_year.reindex(
                columns=[start_year, end_year],
                fill_value=0
            )

            # Minimum baseline for meaningful growth
            min_baseline = 30

            field_year["growth_pct"] = (
                (
                    field_year[end_year]
                    - field_year[start_year]
                )
                / field_year[start_year].replace(
                    0, float("nan")
                )
                * 100
            )

            field_year.loc[
                field_year[start_year] < min_baseline,
                "growth_pct"
            ] = float("nan")

            heatmap_matrix = (
                field_year["growth_pct"]
                .unstack("broad_foe")
                .reindex(selected_countries)
            )

            # Sort countries by latest enrolment volume
            country_order = (
                country_data.sort_values(
                    end_year, ascending=False
                ).index.tolist()
            )

            heatmap_matrix = heatmap_matrix.reindex(
                country_order
            )

            fig_heatmap = px.imshow(
                heatmap_matrix,
                color_continuous_scale="RdYlGn",
                color_continuous_midpoint=0,
                aspect="auto",
                labels={
                    "x": "Field of Education",
                    "y": "Country",
                    "color": "Growth (%)"
                }
            )

            fig_heatmap.update_traces(
                hovertemplate=(
                    "Country: %{y}<br>"
                    "Field: %{x}<br>"
                    "Growth: %{z:.1f}%"
                    "<extra></extra>"
                )
            )

            fig_heatmap.update_xaxes(
                tickangle=-60,
                tickfont=dict(size=9),
                automargin=True
            )

            # ========================================
            # CHART 6 - CONTRIBUTION TO ENROLMENT GROWTH
            # ========================================

            contribution_data = (
                country_data.reset_index()
                .sort_values("growth_abs")
            )

            contribution_data["direction"] = (
                contribution_data["growth_abs"].apply(
                    lambda x: "Growth" if x > 0
                    else "Decline" if x < 0
                    else "No change"
                )
            )

            fig_contribution = px.bar(
                contribution_data,
                x="growth_abs",
                y="country",
                orientation="h",
                color="direction",
                color_discrete_map={
                    "Growth": "#28A879",
                    "Decline": "#E36A63",
                    "No change": "#AAB4BF"
                },
                labels={
                    "growth_abs": "Change in enrolments",
                    "country": "Country",
                    "direction": "Trend"
                },
                hover_data={
                    "growth_abs": ":+,",
                    "growth_pct": ":.1f",
                    "share_pct": ":.2f"
                }
            )

            fig_contribution.add_vline(
                x=0,
                line_color="grey",
                line_width=1
            )

            fig_contribution.update_layout(
                yaxis=dict(
                    categoryorder="array",
                    categoryarray=contribution_data[
                        "country"
                    ].tolist()
                )
            )

            # ========================================
            # CHART FORMATTING
            # ========================================

            chart_height = max(
                420,
                min(850, 180 + len(selected_countries) * 25)
            )

            for fig in [
                fig_positioning,
                fig_heatmap,
                fig_contribution
            ]:
                fig.update_layout(
                    height=chart_height,
                    margin=dict(
                        l=10,
                        r=10,
                        t=35,
                        b=95
                    ),
                    font=dict(size=10),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="left",
                        x=0,
                        font=dict(size=10)
                    )
                )

            fig_positioning.update_layout(
                margin=dict(l=12, r=12, t=55, b=65),
            )

            fig_heatmap.update_layout(
                margin=dict(l=5, r=5, t=35, b=170),
                coloraxis_colorbar=dict(
                    title="Growth %",
                    thickness=10
                )
            )

            # ========================================
            # DISPLAY THREE CHARTS IN ONE ROW
            # ========================================

            col4, col5 = st.columns(
                2,
                gap="medium"
            )

            with col4:
                st.markdown(
                    "**4. International Market Positioning (Excluding Australia)**"
                )
                st.plotly_chart(
                    fig_positioning,
                    use_container_width=True
                )

            with col5:
                st.markdown(
                    "**5. Growth by Country and Field**"
                )
                st.plotly_chart(
                    fig_heatmap,
                    use_container_width=True
                )

            # with col6:
            #     st.markdown(
            #         "**6. Contribution to Enrolment Growth**"
            #     )
            #     st.plotly_chart(
            #         fig_contribution,
            #         use_container_width=True
            #     )

            st.caption(
                f"Market-positioning quadrants use a {share_threshold:.2f}% "
                f"country-share threshold (fixed at 5%). "
                f"Bubble size represents {end_year} enrolments; "
                f"growth compares {start_year} with {end_year}."
            )

            # ----------------------------------------
            # ENROLMENT COVERAGE
            # ----------------------------------------

            enrolment_coverage = country_data["share_pct"].sum()

            st.caption(
                f"Displaying {len(selected_countries)} countries, "
                f"representing {enrolment_coverage:.1f}% of "
                f"international enrolments with known residence "
                f"in {end_year}. "
                f"Heatmap cells require at least "
                f"{min_baseline} baseline enrolments."
            )



    # -----------------------------
    # EXECUTIVE INSIGHT
    # -----------------------------

    st.subheader("Strategic Recommendation")    
    st.info(
        f"Prioritise targeted recruitment campaigns and institutional partnerships in Vietnam, while implementing retention and re-engagement initiatives for Chinese students. In parallel, expand domestic recruitment in high-demand fields."
    )    


elif section == "Competition":

    st.title("Competitive Positioning")
    st.caption(
        "Enrolment growth and changes in competitive share | "
        f"{years[0]}–{years[1]}"
    )

    start_year, end_year = years

    if start_year == end_year:
        st.info("Select two different years to analyse competitive positioning.")

    else:
        # Full five-university reference market
        market_df = df[
            df["ref_year"].isin([start_year, end_year])
        ].copy()

        market_df["ref_year"] = pd.to_numeric(
            market_df["ref_year"], errors="coerce"
        )

        # Calculate enrolments for each institution and year
        university_year = (
            market_df.groupby(["institution", "ref_year"])["enrolments"]
            .sum()
            .unstack(fill_value=0)
            .reindex(columns=[start_year, end_year], fill_value=0)
        )

        # Calculate percentage enrolment growth
        university_year["growth_abs"] = (
            university_year[end_year] - university_year[start_year]
        )

        university_year["growth_pct"] = (
            university_year["growth_abs"]
            / university_year[start_year].replace(0, float("nan"))
            * 100
        )

        # Calculate university share within the five-institution market
        start_total = university_year[start_year].sum()
        end_total = university_year[end_year].sum()

        university_year["share_start"] = (
            university_year[start_year] / start_total * 100
            if start_total > 0 else float("nan")
        )

        university_year["share_end"] = (
            university_year[end_year] / end_total * 100
            if end_total > 0 else float("nan")
        )

        university_year["share_change_pp"] = (
            university_year["share_end"]
            - university_year["share_start"]
        )

        # Apply sidebar university selection only after
        # calculating shares against the full market
        competition_data = (
            university_year.reset_index()
            .rename(columns={
                start_year: "start_enrolments",
                end_year: "end_enrolments"
            })
        )

        competition_data = competition_data[
            competition_data["institution"].isin(institutions)
        ].copy()

        if competitors_only:
            key_institutions = df.loc[
                df["is_key_competitor"].fillna(False),
                "institution"
            ].unique()

            competition_data = competition_data[
                competition_data["institution"].isin(key_institutions)
            ].copy()

        if competition_data.empty:
            st.warning("No universities match the selected filters.")
            st.stop()

        # Short labels for visualisation
        name_map = {
            "Monash University": "Monash",
            "RMIT University": "RMIT",
            "The University of Melbourne": "Melbourne",
            "University of Melbourne": "Melbourne",
            "La Trobe University": "La Trobe",
            "Federation University Australia": "Federation"
        }

        competition_data["university"] = (
            competition_data["institution"]
            .replace(name_map)
        )

        # Key competitors
        key_institutions = set(
            df.loc[
                df["is_key_competitor"].fillna(False),
                "institution"
            ].unique()
        )

        competition_data["competitor_group"] = (
            competition_data["institution"].apply(
                lambda x: "Key UNSW competitor"
                if x in key_institutions
                else "Other university"
            )
        )

        colours = {
            "Key UNSW competitor": "#24569B",
            "Other university": "#8493A7"
        }

        # ==========================================
        # CHART 1 - ENROLMENT GROWTH BY UNIVERSITY
        # ==========================================

        growth_data = competition_data.sort_values(
            "growth_pct", ascending=False
        ).copy()

        fig_growth = px.bar(
            growth_data,
            x="university",
            y="growth_pct",
            color="competitor_group",
            color_discrete_map=colours,
            custom_data=[
                "institution",
                "start_enrolments",
                "end_enrolments",
                "growth_abs"
            ],
            labels={
                "university": "University",
                "growth_pct": "Enrolment growth (%)",
                "competitor_group": "University category"
            }
        )

        fig_growth.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Growth: %{y:+.1f}%<br>"
                "Starting enrolments: %{customdata[1]:,.0f}<br>"
                "Ending enrolments: %{customdata[2]:,.0f}<br>"
                "Absolute change: %{customdata[3]:+,.0f}"
                "<extra></extra>"
            )
        )

        fig_growth.add_hline(
            y=0, line_color="grey", line_width=1
        )

        fig_growth.update_yaxes(ticksuffix="%")

        # ==========================================
        # CHART 2 - CHANGE IN ENROLMENT SHARE
        # ==========================================

        share_data = competition_data.sort_values(
            "share_change_pp", ascending=False
        ).copy()

        fig_share = px.bar(
            share_data,
            x="university",
            y="share_change_pp",
            color="competitor_group",
            color_discrete_map=colours,
            custom_data=[
                "institution",
                "share_start",
                "share_end"
            ],
            labels={
                "university": "University",
                "share_change_pp": "Share change (pp)",
                "competitor_group": "University category"
            }
        )

        fig_share.update_traces(
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Share change: %{y:+.2f} pp<br>"
                "Starting share: %{customdata[1]:.2f}%<br>"
                "Ending share: %{customdata[2]:.2f}%"
                "<extra></extra>"
            )
        )

        fig_share.add_hline(
            y=0, line_color="grey", line_width=1
        )

        fig_share.update_yaxes(ticksuffix=" pp")


        # ==========================================
        # CHART 3 - TOTAL MARKET SHARE BY INSTITUTION
        # ==========================================

        market_share_data = competition_data.sort_values(
            "share_end", ascending=True
        ).copy()

        fig_market_share = px.bar(
            market_share_data,
            x="share_end",
            y="university",
            orientation="h",
            color="competitor_group",
            color_discrete_map=colours,
            text="share_end",
            custom_data=[
                "institution",
                "end_enrolments"
            ],
            labels={
                "share_end": "Market share (%)",
                "university": "University",
                "competitor_group": "University category"
            }
        )

        fig_market_share.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Market share: %{x:.2f}%<br>"
                "Enrolments: %{customdata[1]:,.0f}"
                "<extra></extra>"
            )
        )

        fig_market_share.update_xaxes(
            ticksuffix="%",
            rangemode="tozero"
        )

        fig_market_share.update_layout(
            yaxis=dict(
                title=None,
                categoryorder="total ascending"
            ),
            showlegend=False
        )


        # ==========================================
        # CONSISTENT FORMATTING
        # ==========================================

        for fig in [fig_growth, fig_share, fig_market_share]:
            fig.update_layout(
                height=430,
                margin=dict(l=15, r=15, t=35, b=50),
                font=dict(size=11),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                    font=dict(size=10)
                ),
                xaxis=dict(title=None)
            )

        
        # ==========================================
        # DISPLAY THREE CHARTS SIDE BY SIDE
        # ==========================================

        col1, col2, col3 = st.columns(3, gap="medium")

        with col1:
            st.markdown(
                f"**3. Total Market Share by Institution, "
                f"{end_year}**"
            )
            st.plotly_chart(
                fig_market_share,
                use_container_width=True
            )

        with col2:
            st.markdown(
                f"**1. Enrolment Growth by University, {start_year}–{end_year}**<br>"
                f"*Which universities are growing faster?*",
                unsafe_allow_html=True
            )
            st.plotly_chart(
                fig_growth,
                use_container_width=True
            )

        with col3:
            st.markdown(
                f"**2. Change in Enrolment Share, {start_year}–{end_year}**<br>"
                f"*Which universities are gaining or losing relative competitive position?*",
                unsafe_allow_html=True
            )
            st.plotly_chart(
                fig_share,
                use_container_width=True
            )     

            
    # -----------------------------
    # EXECUTIVE INSIGHT
    # -----------------------------

    st.subheader("Strategic Recommendation")    
    st.info(       
        "Prioritise a competitive benchmarking programme focused on RMIT's "
        "fastest-growing disciplines, student segments and recruitment channels "
        "to identify the drivers of its market-share gains. Use these findings to "
        "target UNSW recruitment investment towards high-growth segments, strengthen "
        "differentiation against Monash and Melbourne"
    )      


elif section == "Portfolio":

    st.title("Student Demand and Portfolio Planning")
    st.caption(
        "Qualification-level demand and academic discipline trends | "
        f"{years[0]}–{years[1]}"
    )

    start_year, end_year = years

    if filtered.empty:
        st.warning("No enrolment records match the selected filters.")
        st.stop()

    if start_year == end_year:
        st.info(
            "Select at least two reporting years to analyse "
            "changes in student demand."
        )

    else:

        # ==========================================
        # CHART 1 - ENROLMENTS BY BROAD COURSE LEVEL
        # ==========================================

        course_data = filtered.copy()

        course_data["Broad Course Level"] = (
            course_data["Broad Course Level"]
            .astype("string")
            .str.strip()
        )

        course_data = course_data[
            course_data["Broad Course Level"].notna()
            & ~course_data["Broad Course Level"].str.casefold().isin(
                ["", "unknown", "not stated"]
            )
        ].copy()

        course_year = (
            course_data.groupby(
                ["Broad Course Level", "ref_year"]
            )["enrolments"]
            .sum()
            .unstack(fill_value=0)
            .reindex(
                columns=[start_year, end_year],
                fill_value=0
            )
        )

        course_year["growth_abs"] = (
            course_year[end_year] - course_year[start_year]
        )

        course_year["growth_pct"] = (
            course_year["growth_abs"]
            / course_year[start_year].replace(0, float("nan"))
            * 100
        )

        # Order qualification levels by latest-year demand
        course_order = (
            course_year.sort_values(
                end_year, ascending=False
            ).index.tolist()
        )

        course_plot = (
            course_year[[start_year, end_year]]
            .reset_index()
            .melt(
                id_vars="Broad Course Level",
                var_name="Year",
                value_name="Enrolments"
            )
        )

        course_plot["Year"] = course_plot["Year"].astype(str)

        fig_course = px.bar(
            course_plot,
            x="Broad Course Level",
            y="Enrolments",
            color="Year",
            barmode="group",
            category_orders={
                "Broad Course Level": course_order,
                "Year": [str(start_year), str(end_year)]
            },
            color_discrete_map={
                str(start_year): "#24569B",
                str(end_year): "#378647"
            },
            labels={
                "Broad Course Level": "Qualification level",
                "Enrolments": "Enrolments"
            }
        )

        fig_course.update_traces(
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Enrolments: %{y:,.0f}"
                "<extra></extra>"
            )
        )

        fig_course.update_layout(
            xaxis_title=None,
            yaxis_title="Enrolments"
        )

        
        # ==========================================
        # CHART 2 - GROWTH OPPORTUNITY MATRIX
        # ==========================================

        import plotly.graph_objects as go

        # Full five-university reference market.
        # Do not apply the sidebar university filter
        # to the overall market-growth calculation.
        market_fields = df[
            df["ref_year"].isin([start_year, end_year])
        ].copy()

        # Identify key UNSW competitors from the reference table
        competitor_fields = market_fields[
            market_fields["is_key_competitor"].fillna(False)
        ].copy()

        def calculate_field_growth(data, prefix):
            """Calculate field-level enrolment growth."""
            summary = (
                data.groupby(["broad_foe", "ref_year"])["enrolments"]
                .sum()
                .unstack(fill_value=0)
                .reindex(
                    columns=[start_year, end_year],
                    fill_value=0
                )
            )

            summary[f"{prefix}_growth"] = (
                (summary[end_year] - summary[start_year])
                / summary[start_year].replace(0, float("nan"))
                * 100
            )

            return summary.rename(columns={
                start_year: f"{prefix}_start",
                end_year: f"{prefix}_end"
            })[
                [
                    f"{prefix}_start",
                    f"{prefix}_end",
                    f"{prefix}_growth"
                ]
            ]

        # Overall field growth across all universities
        overall_growth = calculate_field_growth(
            market_fields, "overall"
        )

        # Field growth among key UNSW competitors
        competitor_growth = calculate_field_growth(
            competitor_fields, "competitor"
        )

        # Combine both dimensions
        opportunity = overall_growth.join(
            competitor_growth,
            how="inner"
        ).reset_index()

        # Exclude fields with insufficient baseline volume
        min_baseline = 30

        opportunity = opportunity[
            (opportunity["overall_start"] >= min_baseline)
            & (opportunity["competitor_start"] >= min_baseline)
            & opportunity["overall_growth"].notna()
            & opportunity["competitor_growth"].notna()
            & (opportunity["overall_end"] > 0)
        ].copy()

        # Classify each field into the four quadrants
        def classify_opportunity(row):
            x = row["overall_growth"]
            y = row["competitor_growth"]

            if x >= 0 and y >= 0:
                return "Strong demand alignment"
            elif x < 0 and y >= 0:
                return "Competitor-led growth"
            elif x >= 0 and y < 0:
                return "Broader market growth"
            else:
                return "Lower growth / review"

        opportunity["quadrant"] = opportunity.apply(
            classify_opportunity, axis=1
        )

        # ==========================================
        # BUILD BUBBLE CHART
        # ==========================================

        fig_opportunity = px.scatter(
            opportunity,
            x="overall_growth",
            y="competitor_growth",
            size="overall_end",
            color="quadrant",
            hover_name="broad_foe",
            size_max=48,
            color_discrete_map={
                "Strong demand alignment": "#28A879",
                "Competitor-led growth": "#5586D5",
                "Broader market growth": "#D5A021",
                "Lower growth / review": "#E36A63"
            },
            custom_data=[
                "overall_start",
                "overall_end",
                "competitor_start",
                "competitor_end"
            ],
            labels={
                "overall_growth": "Overall field growth (%)",
                "competitor_growth": "Key competitor growth (%)",
                "overall_end": "Latest-year enrolments",
                "quadrant": "Opportunity category"
            }
        )

        fig_opportunity.update_traces(
            marker=dict(
                line=dict(width=1.5, color="white"),
                opacity=0.85
            ),
            hovertemplate=(
                "<b>%{hovertext}</b><br>"
                "Overall growth: %{x:+.1f}%<br>"
                "Competitor growth: %{y:+.1f}%<br>"
                "Overall enrolments (start): %{customdata[0]:,.0f}<br>"
                "Overall enrolments (end): %{customdata[1]:,.0f}<br>"
                "Competitor enrolments (start): %{customdata[2]:,.0f}<br>"
                "Competitor enrolments (end): %{customdata[3]:,.0f}"
                "<extra></extra>"
            )
        )

        # Zero-growth boundaries
        fig_opportunity.add_hline(
            y=0,
            line_dash="dash",
            line_color="#8793A3",
            line_width=1.5
        )

        fig_opportunity.add_vline(
            x=0,
            line_dash="dash",
            line_color="#8793A3",
            line_width=1.5
        )

        # Quadrant labels positioned in chart coordinates
        if not opportunity.empty:
            x_min = min(opportunity["overall_growth"].min(), 0)
            x_max = max(opportunity["overall_growth"].max(), 0)
            y_min = min(opportunity["competitor_growth"].min(), 0)
            y_max = max(opportunity["competitor_growth"].max(), 0)

            x_pad = max((x_max - x_min) * 0.15, 2)
            y_pad = max((y_max - y_min) * 0.15, 2)

            x_min -= x_pad
            x_max += x_pad
            y_min -= y_pad
            y_max += y_pad

            fig_opportunity.update_xaxes(
                range=[x_min, x_max],
                ticksuffix="%"
            )

            fig_opportunity.update_yaxes(
                range=[y_min, y_max],
                ticksuffix="%"
            )

            quadrant_labels = [
                ("Competitor-led growth - Overall field declining, but key competitors growing", x_min / 2, y_max * 0.85),
                ("Strong demand alignment - Both field and key competitors growing", x_max / 2, y_max * 0.85),
                ("Lower growth / review - Both field and competitor declining", x_min / 2, y_min * 0.85),
                ("Broader market growth - Overall field growing, but key competitors declining", x_max / 2, y_min * 0.85)
            ]

            for label, x, y in quadrant_labels:
                fig_opportunity.add_annotation(
                    x=x,
                    y=y,
                    text=label,
                    showarrow=False,
                    font=dict(size=10, color="#9CA9B8"),
                    opacity=0.8
                )

        fig_opportunity.update_layout(
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=9)
            )
        )


        # ==========================================
        # CONSISTENT FORMATTING
        # ==========================================

        for fig in [fig_course, fig_opportunity]:
            fig.update_layout(
                height=480,
                margin=dict(l=15, r=15, t=40, b=90),
                font=dict(size=11),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="left",
                    x=0,
                    font=dict(size=10)
                )
            )

        fig_course.update_xaxes(
            tickangle=-30,
            automargin=True
        )

        fig_opportunity.update_yaxes(
            automargin=True
        )

        # ==========================================
        # DISPLAY TWO CHARTS SIDE BY SIDE
        # ==========================================

        col1, col2 = st.columns(2, gap="medium")

        with col1:
            st.markdown(
                f"**1. Enrolments by Broad Course Level**<br>"
                f"*Which qualification levels are experiencing the strongest demand?*",
                unsafe_allow_html=True
            )          

            st.plotly_chart(
                fig_course,
                use_container_width=True
            )

        with col2:
            st.markdown(
                f"**2. Growth Opportunity Matrix**<br>"
                f"*Which academic disciplines are experiencing increasing or declining demand?*",
                unsafe_allow_html=True
            )
            st.plotly_chart(
                fig_opportunity,
                use_container_width=True
            ) 

    # -----------------------------
    # EXECUTIVE INSIGHT
    # -----------------------------

    st.subheader("Strategic Recommendation")    
    st.info(       
        "Prioritise programme expansion and targeted recruitment in growing disciplines, "
        "while benchmarking competitor offerings in Information Technology and Management and Commerce to identify "
        "opportunities for differentiation and market-share capture. "
        "Review declining postgraduate demand and use field-specific growth, competitor "
        "performance and enrolment volumes to guide annual portfolio "
        "investment and rationalisation decisions"
    )         


elif section == "Student Demand":

    st.title("Student Demand Characteristics")
    st.caption(
        "Student progression and attendance composition | "
        f"{years[0]}–{years[1]}"
    )

    if filtered.empty:
        st.warning("No enrolment records match the selected filters.")
        st.stop()

    # ==========================================
    # CHART 1 - COMMENCING VS CONTINUING
    # ==========================================

    commencement_data = filtered.copy()

    # Inspect and standardise commencing indicator
    commencement_data["student_status"] = (
        commencement_data["comm_indicator"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .map({
            "commencing": "Commencing",
            "non-commencing": "Non-commencing"
        })
    )

    commencement_data = commencement_data[
        commencement_data["student_status"].notna()
    ].copy()

    commencement_year = (
        commencement_data.groupby(
            ["ref_year", "student_status"],
            as_index=False
        )["enrolments"].sum()
    )

    # Share of commencing students in each year
    commencement_year["share_pct"] = (
        commencement_year["enrolments"]
        / commencement_year.groupby("ref_year")[
            "enrolments"
        ].transform("sum")
        * 100
    )

    fig_commencement = px.line(
        commencement_year,
        x="ref_year",
        y="enrolments",
        color="student_status",
        markers=True,
        category_orders={
            "student_status": [
                "Commencing",
                "Non-commencing"
            ]
        },
        color_discrete_map={
            "Commencing": "#24569B",
            "Non-commencing": "#378647"
        },
        custom_data=["share_pct"],
        labels={
            "ref_year": "Year",
            "enrolments": "Enrolments",
            "student_status": "Student status"
        }
    )

    fig_commencement.update_traces(
        line=dict(width=3),
        marker=dict(size=9),
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Year: %{x}<br>"
            "Enrolments: %{y:,.0f}<br>"
            "Share: %{customdata[0]:.1f}%"
            "<extra></extra>"
        )
    )

    fig_commencement.update_xaxes(
        tickmode="array",
        tickvals=sorted(
            commencement_year["ref_year"].unique()
        ),
        dtick=1
    )

    fig_commencement.update_yaxes(
        rangemode="tozero"
    )

    # ==========================================
    # CHART 2 - FULL-TIME VS PART-TIME
    # ==========================================

    attendance_data = filtered.copy()

    attendance_data["attendance_type"] = (
        attendance_data["type_of_attendance"]
        .astype("string")
        .str.strip()
        .str.casefold()
        .map({
            "full-time": "Full-time",
            "full time": "Full-time",
            "full-time attendance": "Full-time",
            "part-time": "Part-time",
            "part time": "Part-time",
            "part-time attendance": "Part-time"
        })
    )

    attendance_data = attendance_data[
        attendance_data["attendance_type"].notna()
    ].copy()

    attendance_year = (
        attendance_data.groupby(
            ["ref_year", "attendance_type"],
            as_index=False
        )["enrolments"].sum()
    )

    attendance_year["share_pct"] = (
        attendance_year["enrolments"]
        / attendance_year.groupby("ref_year")[
            "enrolments"
        ].transform("sum")
        * 100
    )

    fig_attendance = px.bar(
        attendance_year,
        x="ref_year",
        y="share_pct",
        color="attendance_type",
        barmode="stack",
        category_orders={
            "attendance_type": [
                "Full-time",
                "Part-time"
            ]
        },
        color_discrete_map={
            "Full-time": "#24569B",
            "Part-time": "#378647"
        },
        custom_data=["enrolments"],
        labels={
            "ref_year": "Year",
            "share_pct": "Share of enrolments (%)",
            "attendance_type": "Attendance type"
        }
    )

    fig_attendance.update_traces(
        hovertemplate=(
            "<b>%{fullData.name}</b><br>"
            "Year: %{x}<br>"
            "Share: %{y:.1f}%<br>"
            "Enrolments: %{customdata[0]:,.0f}"
            "<extra></extra>"
        )
    )

    fig_attendance.update_yaxes(
        range=[0, 100],
        ticksuffix="%"
    )

    fig_attendance.update_xaxes(
        tickmode="array",
        tickvals=sorted(
            attendance_year["ref_year"].unique()
        )
    )

    # ==========================================
    # CONSISTENT CHART FORMATTING
    # ==========================================

    for fig in [fig_commencement, fig_attendance]:
        fig.update_layout(
            height=450,
            margin=dict(l=15, r=15, t=45, b=45),
            font=dict(size=11),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=10)
            ),
            xaxis_title=None
        )

    # ==========================================
    # DISPLAY TWO CHARTS SIDE BY SIDE
    # ==========================================

    col1, col2 = st.columns(2, gap="medium")

    with col1:
        st.markdown(
            f"**1. Commencing versus Continuing Students**<br>"
            f"*Are enrolment changes driven by new students or existing student cohorts?*",
            unsafe_allow_html=True
        )
        st.plotly_chart(
            fig_commencement,
            use_container_width=True
        )

    with col2:
        st.markdown(
            f"**2. Full-time versus Part-time Attendance**<br>"
            f"*Is the composition of study modes changing?*",
            unsafe_allow_html=True
        )
        st.plotly_chart(
            fig_attendance,
            use_container_width=True
        )

    # ==========================================
    # SUMMARY METRICS
    # ==========================================

    st.divider()
    st.subheader("Student Demand Indicators")

    latest_year = years[1]

    latest_commencement = commencement_year[
        commencement_year["ref_year"] == latest_year
    ]

    latest_attendance = attendance_year[
        attendance_year["ref_year"] == latest_year
    ]

    commencing_share = latest_commencement.loc[
        latest_commencement["student_status"] == "Commencing",
        "share_pct"
    ]

    fulltime_share = latest_attendance.loc[
        latest_attendance["attendance_type"] == "Full-time",
        "share_pct"
    ]

    k1, k2 = st.columns(2)

    k1.metric(
        f"Commencing share ({latest_year})",
        f"{commencing_share.iloc[0]:.1f}%"
        if not commencing_share.empty else "N/A"
    )

    k2.metric(
        f"Full-time share ({latest_year})",
        f"{fulltime_share.iloc[0]:.1f}%"
        if not fulltime_share.empty else "N/A"
    )

    # -----------------------------
    # EXECUTIVE INSIGHT
    # -----------------------------

    st.subheader("Strategic Recommendation")    
    st.info(       
        "Strengthen new student recruitment through targeted campaigns "
        "and improved applicant conversion, while expanding flexible study " 
        "options to meet growing part-time demand. Monitor intake, retention " 
        "and attendance trends to guide programme planning"
    )    

else:
    st.info("This section will be developed in the next stage.")


