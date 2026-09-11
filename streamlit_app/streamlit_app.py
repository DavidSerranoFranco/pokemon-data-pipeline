"""
Pokemon Pipeline Streamlit App
Dashboard interactive that use BigQuery
"""

import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# Configuration Page
st.set_page_config(
    page_title="Pokemon Analytics Dashboard",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Bigquery Conection
@st.cach_resource
def get_bigquery_client():
    """Create a BigQuery client using service account credentials."""
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')

    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(credentials=credentials)
    else:
        # Use default credentials if no service account is provided
        return bigquery.Client()

# Consult BigQuery+
@st.cache_data(ttl=300)
def load_pokemon_data():
    """Load Pokemon data from BigQuery."""
    client = get_bigquery_client()

    query = """
    SELECT
        pokemon_id,
        pokemon_name,
        height_cm,
        weight_grams,
        types,
        abilities,
        categorized_weight
    FROM `inbound-theory-500201-u4.pokemon_dbt_dev.dim_pokemon`
    ORDER BY pokemon_id
    """

    df = client.query(query).to_dataframe()
    return df

@st.cache_data(ttl=300)
def load_pokemon_stats():
    """Load Pokemon stats from BigQuery."""
    client = get_bigquery_client()

    query = """
    SELECT 
        pokemon_id,
        pokemon_name,
        height_cm,
        weight_g,
        size_index
    FROM `inbound-theory-500201-u4.pokemon_dbt_dev.fct_pokemon_stats`
    ORDER BY size_index DESC
    """

    df = client.query(query).to_dataframe()
    return df


# Main UI
def main():
    # Title and description
    st.title("Pokemon analytics Dashboard")
    st.markdown("**Modern Pipeline ELT**: API -> GCS -> BigQuery -> dbt -> Streamlit")
    st.markdown("---")

    # Load data
    try:
        df_pokemon = load_pokemon_data()
        df_stats = load_pokemon_stats()
    except Exception as e:
        st.error(f"Error loading data from BigQuery: {e}")
        st.stop()

    # sidebar filters
    st.sidebar.header("Filters")

    # Category weight filter
    weight_filter = st.sidebar.multiselect(
        "Select Weight Category",
        options=df_pokemon["categorized_weight"].unique(),
        default=df_pokemon["categorized_weight"].unique()
    )

    # Type filter
    all_type = []
    for types_list in df_pokemon["types"]:
        if isinstance(types_list, list):
            all_types.extend(types_list)
        elif isinstance(types_list, str):
            all_types.append(types_list)
    all_types = list(set(all_types))

    type_filter = st.sidebar.multiselect(
        "Type(s):",
        options=sorted(all_types),
        default=sorted(all_types)
    )

    # Apply filters
    df_filtered = df_pokemon[
        df_pokemon["categorized_weight"].isin(weight_filter)
    ].copy()

    if type_filter:
        mask = df_filtered["types"].apply(
            lambda x: any(
                t in x for t in type_filter
            ) if isinstance(x, list) else x in type_filter
        )
        df_filtered = df_filtered[mask]

    # KPIs and Metrics
    st.subheader("Key Performance Indicators (KPIs)")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Pokemon",
            value=len(df_filtered),
            delta=None
        )

    with col2:
        avg_height = df_filtered["height_cm"].mean()
        st.metric(
            label="Average Height (cm)",
            value=f"{avg_height:.1f}",
            delta=None
        )

    with col3:
        avg_weight = df_filtered["weight_g"].mean() / 100
        st.metric(
            label="Average Weight (kg)",
            value=f"{avg_weight:.1f}",
            delta=None
        )

    with col4:
        heaviest = df_filtered.loc[df_filtered["weight_g"].idxmax()]
        st.metric(
            label="Heaviest Pokemon",
            value=heaviest["pokemon_name"],
            delta=f"{heaviest['weight_g']/100:.1f} kg"
        )

    st.markdown("---")

    # Display filtered data
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Height vs Weight")

        # Scatter plot
        st.scatter_chart(
            df_filtered,
            x="height_cm",
            y="weight_g",
            use_container_width=True
        )

        st.caption("Each point represents a Pokémon")

    with col2:
        st.subheader("🏋️ Distribution by Weight Category")

        # Bar chart
        peso_counts = df_filtered[
            "categorized_weight"
        ].value_counts().reset_index()
        peso_counts.columns = ["Category", "Count"]

        st.bar_chart(
            peso_counts.set_index("Category"),
            use_container_width=True
        )

    st.markdown("---")

    # Top 10 Pokemon by Size Index
    st.subheader("Top 10 Pokemon by Size Index")

    df_stats_filtered = df_stats[
        df_stats["pokemon_id"].isin(df_filtered["pokemon_id"])
    ]

    top_10 = df_stats_filtered.head(10)

    st.dataframe(
        top_10[["pokemon_name", "height_cm", "weight_g", "size_index"]],
        use_container_width=True,
        hide_index=True
    )

    # Complete Pokemon Table
    st.markdown("---")
    st.subheader("📋 Complete Pokemon Database")

    # Show filtered data in a table
    st.dataframe(
        df_filtered[[
            "pokemon_id",
            "pokemon_name",
            "height_cm",
            "weight_g",
            "types",
            "peso_categoria"
        ]],
        use_container_width=True,
        hide_index=True
    )

    # Footer
    st.markdown("---")
    st.markdown("""
    **Technologies:** Python | Apache Airflow | Google Cloud Storage | BigQuery | dbt | Streamlit
    **Architecture:** Medallion (Bronze → Silver → Gold)
    **Author:** David Serrano Franco
    """)

if __name__ == "__main__":
    main()
