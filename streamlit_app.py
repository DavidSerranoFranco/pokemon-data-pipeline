"""
Pokemon Pipeline Streamlit App
Interactive dashboard using BigQuery
"""

import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account
import os

# PAGE CONFIGURATION
st.set_page_config(
    page_title="Pokémon Analytics Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# BIGQUERY CONNECTION
@st.cache_resource
def get_bigquery_client():
    """Create a BigQuery client using service account credentials."""
    # Try reading from Streamlit Secrets (Production)
    if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
        credentials = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return bigquery.Client(credentials=credentials)

    # Fallback to local environment variables (Development)
    credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        return bigquery.Client(credentials=credentials)
    else:
        return bigquery.Client()

# DATA LOADING FUNCTIONS
@st.cache_data(ttl=300)
def load_pokemon_data():
    """Load Pokemon data from BigQuery."""
    client = get_bigquery_client()

    # CORREGIDO: weight_g y peso_categoria coinciden con tu modelo dbt
    query = """
    SELECT
        pokemon_id,
        pokemon_name,
        height_cm,
        weight_g,
        types,
        abilities,
        peso_categoria
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

# MAIN UI
def main():
    st.title("⚡ Pokémon Analytics Dashboard")
    st.markdown("**Modern ELT Pipeline**: API → GCS → BigQuery → dbt → Streamlit")
    st.markdown("---")

    # Load data
    try:
        df_pokemon = load_pokemon_data()
        df_stats = load_pokemon_stats()
    except Exception as e:
        st.error(f"Error loading data from BigQuery: {e}")
        st.stop()

    # SIDEBAR FILTERS
    st.sidebar.header("🔍 Filters")

    # Weight category filter
    weight_filter = st.sidebar.multiselect(
        "Weight Category",
        options=sorted(df_pokemon["peso_categoria"].dropna().unique()),
        default=sorted(df_pokemon["peso_categoria"].dropna().unique())
    )

    # Type filter (Robust extraction handling both strings and lists)
    all_types = set()
    for types_val in df_pokemon["types"]:
        if pd.isna(types_val):
            continue
        if isinstance(types_val, str):
            all_types.update(types_val.split(","))
        elif isinstance(types_val, list):
            all_types.update(types_val)

    all_types = sorted(list(all_types))

    type_filter = st.sidebar.multiselect(
        "Type(s)",
        options=all_types,
        default=all_types
    )

    # Apply filters
    df_filtered = df_pokemon[
        df_pokemon["peso_categoria"].isin(weight_filter)
    ].copy()

    if type_filter:
        def check_type(row_types):
            if pd.isna(row_types):
                return False
            row_types_list = str(row_types).split(",")
            return any(t in row_types_list for t in type_filter)

        mask = df_filtered["types"].apply(check_type)
        df_filtered = df_filtered[mask]

    # KPIs AND METRICS
    st.subheader("📊 Key Performance Indicators (KPIs)")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(label="Total Pokémon", value=len(df_filtered))

    with col2:
        avg_height = df_filtered["height_cm"].mean()
        st.metric(label="Avg Height (cm)", value=f"{avg_height:.1f}")

    with col3:
        avg_weight = df_filtered["weight_g"].mean() / 100
        st.metric(label="Avg Weight (kg)", value=f"{avg_weight:.1f}")

    with col4:
        if not df_filtered.empty:
            heaviest = df_filtered.loc[df_filtered["weight_g"].idxmax()]
            st.metric(
                label="Heaviest Pokémon",
                value=heaviest["pokemon_name"].title(),
                delta=f"{heaviest['weight_g']/100:.1f} kg"
            )
        else:
            st.metric(label="Heaviest Pokémon", value="N/A")

    st.markdown("---")

    # CHARTS
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Height vs Weight")
        st.scatter_chart(
            df_filtered,
            x="height_cm",
            y="weight_g",
            use_container_width=True
        )
        st.caption("Each point represents a Pokémon")

    with col2:
        st.subheader("🏋️ Distribution by Weight Category")
        peso_counts = df_filtered["peso_categoria"].value_counts().reset_index()
        peso_counts.columns = ["Category", "Count"]

        st.bar_chart(
            peso_counts.set_index("Category"),
            use_container_width=True
        )

    st.markdown("---")

    # TOP 10 POKEMON
    st.subheader("🏆 Top 10 Pokémon by Size Index")

    df_stats_filtered = df_stats[
        df_stats["pokemon_id"].isin(df_filtered["pokemon_id"])
    ]

    top_10 = df_stats_filtered.head(10)

    st.dataframe(
        top_10[["pokemon_name", "height_cm", "weight_g", "size_index"]],
        use_container_width=True,
        hide_index=True
    )

    # COMPLETE TABLE
    st.markdown("---")
    st.subheader("📋 Complete Pokémon Database")

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

    # FOOTER
    st.markdown("---")
    st.markdown("""
    **Technologies:** Python | Apache Airflow | Google Cloud Storage | BigQuery | dbt | Streamlit  
    **Architecture:** Medallion (Bronze → Silver → Gold)  
    **Author:** David Serrano Franco
    """)

if __name__ == "__main__":
    main()
