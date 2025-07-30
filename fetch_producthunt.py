import os
import requests
import pandas as pd
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

load_dotenv('producthunt.env')

# Step 1: Get client_id and client_secret from environment variables
CLIENT_ID = os.getenv("PRODUCTHUNT_CLIENT_ID")
CLIENT_SECRET = os.getenv("PRODUCTHUNT_CLIENT_SECRET")

# Step 2: Define URLs
TOKEN_URL = "https://api.producthunt.com/v2/oauth/token"
GRAPHQL_URL = "https://api.producthunt.com/v2/api/graphql"

# Step 3: Function to get OAuth2 access token
def get_access_token():
    response = requests.post(TOKEN_URL, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    })
    print(response.json())  # Optional: remove or comment this line in production
    if response.status_code != 200:
        raise Exception(f"Failed to get access token: {response.text}")
    return response.json()["access_token"]

# Step 4: GraphQL query template (without makerInside)
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

# Step 5: Helper function to get past N days as date list
def get_past_days(n=21):
    today = datetime.now(timezone.utc).date()
    return [today - timedelta(days=i) for i in range(n)]

# Step 6: Function to fetch top products per day
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
        print(response.json())  # Optional: remove or comment this line in production
        if response.status_code != 200:
            print(f"Warning: Failed to fetch data for {day}")
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

# Step 7: Main execution
if __name__ == "__main__":
    try:
        token = get_access_token()
        df = fetch_top_products(token)
        pd.set_option("display.max_rows", None)
        print("\nTop 10 Most Upvoted Products per Day (Last 21 Days):\n")
        print(df.to_string(index=False))
        
        today_str = datetime.now().strftime("%Y-%m-%d")

        # Save as Excel
        excel_filename = f"producthunt_top_products_{today_str}.xlsx"
        df.to_excel(excel_filename, index=False)
        print(f"\nExcel file saved as '{excel_filename}'")

        # Save as HTML
        html_filename = f"producthunt_top_products_{today_str}.html"
        df.to_html(html_filename, index=False, classes="table table-striped")
        print(f"HTML file saved as '{html_filename}'")

    except Exception as e:
        print(f"Error: {e}")