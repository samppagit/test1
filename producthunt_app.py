import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta, timezone

# Get credentials from Streamlit Secrets
CLIENT_ID = st.secrets["PRODUCTHUNT_CLIENT_ID"]
CLIENT_SECRET = st.secrets["PRODUCTHUNT_CLIENT_SECRET"]

# API URLs
TOKEN_URL = "https://api.producthunt.com/v2/oauth/token"
GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

# Get access token from Product Hunt
def get_access_token():
    response = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    })
    if response.status_code != 200:
        raise Exception(f"Failed to get access token: {response.text}")
    return response.json()["access_token"]

# GraphQL query
GRAPHQL_QUERY = """
query ($date: DateTime!, $dateEnd: DateTime!) {
  posts(first: 10, order: VOTES, postedAfter: $date, postedBefore: $dateEnd) {
    edges {
      node {
        name
        tagline
        votesCount
        url
      }
    }
  }
}
"""

# Get past n days
def get_past_days(n=21):
    today = datetime.now(timezone.utc).date()
    return [today - timedelta(days=i) for i in range(n)]

# Fetch data
def fetch_top_products(access_token, days=21, top_n=10):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    results = []
    for day in get_past_days(days):
        start_time = datetime.combine(day, datetime.min.time()).isoformat() + "Z"
        end_time = datetime.combine(day, datetime.max.time()).isoformat() + "Z"
        variables = {
            "date": start_time,
            "dateEnd": end_time
        }
        response = requests.post(GRAPHQL_URL, headers=headers, json={
            "query": GRAPHQL_QUERY,
            "variables": variables
        })
        if response.status_code != 200:
            st.warning(f"Failed to fetch data for {day}")
            continue
        posts = response.json()["data"]["posts"]["edges"]
        for post in posts[:top_n]:
            node = post["node"]
            results.append({
                "date": day.isoformat(),
                "product_name": node["name"],
                "tagline": node.get("tagline", ""),
                "upvotes": node["votesCount"],
                "url": node["url"]
            })
    return pd.DataFrame(results)

# Streamlit App Layout
st.title("🚀 Product Hunt Top Products (Last 21 Days)")
st.write("Displays the top 10 most upvoted products for each day.")

try:
    token = get_access_token()
    df = fetch_top_products(token)
    st.dataframe(df)

    # Download as Excel
    today_str = datetime.now().strftime("%Y-%m-%d")
    excel_filename = f"producthunt_top_products_{today_str}.xlsx"
    df.to_excel(excel_filename, index=False)

    with open(excel_filename, "rb") as f:
        st.download_button(
            label="📥 Download Excel file",
            data=f,
            file_name=excel_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

except Exception as e:
    st.error(f"Error: {e}")
