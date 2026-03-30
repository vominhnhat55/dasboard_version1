# queries/bq_client.py
# Khởi tạo BigQuery client — dùng chung toàn app
# ─────────────────────────────────────────────────────────────────────────────

import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
from config import BQ_PROJECT


@st.cache_resource
def get_client() -> bigquery.Client:
    """
    Tạo BigQuery client từ st.secrets.
    @cache_resource: tạo 1 lần duy nhất, dùng lại cho mọi request.

    Secrets cần có trong .streamlit/secrets.toml:
        [gcp_service_account]
        type = "service_account"
        project_id = "..."
        ...
    """
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    return bigquery.Client(project=BQ_PROJECT, credentials=credentials)


def run_query(sql: str) -> "pd.DataFrame":
    """Chạy SQL và trả về DataFrame. Dùng client đã cache."""
    from queries.bq_client import get_client
    return get_client().query(sql).to_dataframe()
