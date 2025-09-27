import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Output, Input
from datetime import date, timedelta
from dotenv import load_dotenv
import os
import pycountry
from openai import OpenAI

# ------------------------------
# ENV CONFIG
# ------------------------------
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")
ZONE_ID = os.getenv("ZONE_ID")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}
url = "https://api.cloudflare.com/client/v4/graphql"

# Paralympics medallists JSON feed
MEDALLISTS_URL = (
    "https://lrs-atvr25-azefd5ddhyajaah5.a02.azurefd.net/"
    "data/GLO_Medallists~comp=ATVR25~lang=ENG.json"
)
MEDAL_MAP = {"1": "Gold", "2": "Silver", "3": "Bronze"}


# ------------------------------
# HELPERS
# ------------------------------
def convert_country_codes(df):
    """Convert 2-letter codes to 3-letter for Plotly choropleth."""
    def to_iso3(code):
        try:
            return pycountry.countries.get(alpha_2=code).alpha_3
        except:
            return None
    df["iso_alpha3"] = df["country"].apply(to_iso3)
    return df.dropna(subset=["iso_alpha3"])


# ------------------------------
# CLOUDFLARE DATA
# ------------------------------
def fetch_timeseries(days=7):
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    query = f"""
    {{
      viewer {{
        zones(filter: {{ zoneTag: "{ZONE_ID}" }}) {{
          httpRequests1dGroups(
            limit: {days}
            filter: {{ date_geq: "{start_date}", date_leq: "{end_date}" }}
            orderBy: [date_ASC]
          ) {{
            dimensions {{ date }}
            sum {{
              requests
              cachedRequests
              bytes
              cachedBytes
              threats
            }}
          }}
        }}
      }}
    }}
    """
    resp = requests.post(url, headers=headers, json={"query": query})
    data = resp.json()
    groups = data["data"]["viewer"]["zones"][0]["httpRequests1dGroups"]

    df = pd.DataFrame([{
        "date": g["dimensions"]["date"],
        "requests": g["sum"]["requests"],
        "cachedRequests": g["sum"]["cachedRequests"],
        "bytes": g["sum"]["bytes"],
        "cachedBytes": g["sum"]["cachedBytes"],
        "threats": g["sum"]["threats"],
    } for g in groups])
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_country_data(days=7):
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    query = f"""
    {{
      viewer {{
        zones(filter: {{ zoneTag: "{ZONE_ID}" }}) {{
          httpRequests1dGroups(
            limit: 1
            filter: {{ date_geq: "{start_date}", date_leq: "{end_date}" }}
          ) {{
            sum {{
              countryMap {{
                clientCountryName
                requests
                bytes
                threats
              }}
            }}
          }}
        }}
      }}
    }}
    """
    resp = requests.post(url, headers=headers, json={"query": query})
    data = resp.json()
    countries = (
        data["data"]["viewer"]["zones"][0]["httpRequests1dGroups"][0]["sum"]["countryMap"]
    )

    df = pd.DataFrame(countries)
    df = df.rename(columns={"clientCountryName": "country"})
    df = df.sort_values("requests", ascending=False)
    df = convert_country_codes(df)
    return df


# ------------------------------
# PARALYMPICS DATA
# ------------------------------
def fetch_medallists():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://lrs-atvr25-azefd5ddhyajaah5.a02.azurefd.net/",
        "Origin": "https://lrs-atvr25-azefd5ddhyajaah5.a02.azurefd.net",
    }
    resp = requests.get(MEDALLISTS_URL, headers=headers)
    resp.raise_for_status()
    return resp.json().get("medallist", [])


def parse_medallists(raw):
    parsed = []
    for item in raw:
        medal_type = MEDAL_MAP.get(item.get("medal_type"), "Unknown")
        event = item.get("event", {}).get("longDescription", "")
        athlete_info = item.get("athletes", [{}])[0].get("athlete", {})
        athlete_name = athlete_info.get("name", "Unknown Athlete")
        country_code = athlete_info.get("organisation", {}).get("code", "UNK")
        country_name = athlete_info.get("organisation", {}).get("description", "Unknown Country")
        parsed.append({
            "athlete": athlete_name,
            "country": country_name,
            "country_code": country_code,
            "medal": medal_type,
            "event": event
        })
    return parsed


def compute_medal_stats(medallists):
    total = len(medallists)
    by_country = {}
    medal_tally = {}
    for m in medallists:
        country = m["country"]
        medal = m["medal"]
        if country not in medal_tally:
            medal_tally[country] = {"Gold": 0, "Silver": 0, "Bronze": 0, "Total": 0}
        medal_tally[country][medal] += 1
        medal_tally[country]["Total"] += 1
        by_country[country] = by_country.get(country, 0) + 1
    return {
        "total_medals": total,
        "by_country": by_country,
        "medal_tally": medal_tally,
        "medallists": medallists
    }


def generate_medallist_summary(stats):
    if not stats["total_medals"]:
        return "No medals awarded today yet."
    prompt = (
        f"Write a short Paralympics summary. "
        f"Total medals: {stats['total_medals']}. "
        f"Top countries: {list(stats['by_country'].keys())[:5]}. "
        f"Keep it under 50 words, uplifting and neutral."
    )
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content.strip()


def generate_medalist_messages(medallists):
    return [
        f"🏅 {m['athlete']} ({m['country']}) won {m['medal']} in {m['event']}!"
        for m in medallists
    ]


# ------------------------------
# DASH APP
# ------------------------------
app = Dash(__name__)

# Enhanced CSS styles - External stylesheet approach
external_stylesheets = [
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
]

app = Dash(__name__, external_stylesheets=external_stylesheets)

# Add custom CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            
            .dashboard-container {
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(20px);
                border-radius: 24px;
                margin: 20px;
                padding: 32px;
                box-shadow: 0 25px 50px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            
            .header-section {
                text-align: center;
                margin-bottom: 40px;
                position: relative;
            }
            
            .main-title {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                font-size: 3rem;
                font-weight: 700;
                letter-spacing: -0.02em;
                margin-bottom: 12px;
            }
            
            .subtitle {
                color: #6b7280;
                font-size: 1.2rem;
                font-weight: 400;
                margin-bottom: 20px;
            }
            
            .divider {
                width: 120px;
                height: 4px;
                background: linear-gradient(90deg, #667eea, #764ba2);
                border: none;
                border-radius: 2px;
                margin: 0 auto;
            }
            
            .section-card {
                background: white;
                border-radius: 16px;
                padding: 24px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                border: 1px solid rgba(0, 0, 0, 0.06);
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                height: 100%;
            }
            
            .section-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
            }
            
            .section-title {
                color: #1f2937;
                font-size: 1.5rem;
                font-weight: 600;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .icon {
                font-size: 1.8rem;
            }
            
            .stat-card {
                background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
                color: white;
                padding: 20px;
                border-radius: 12px;
                text-align: center;
                min-width: 160px;
                transition: all 0.3s ease;
                box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
            }
            
            .stat-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(79, 70, 229, 0.4);
            }
            
            .stat-card.green {
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
            }
            
            .stat-card.blue {
                background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
                box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
            }
            
            .stat-card.red {
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                box-shadow: 0 4px 15px rgba(239, 68, 68, 0.3);
            }
            
            .stat-value {
                font-size: 1.8rem;
                font-weight: 700;
                margin-bottom: 4px;
            }
            
            .stat-label {
                font-size: 0.9rem;
                opacity: 0.9;
                font-weight: 500;
            }
            
            .dropdown-container {
                display: flex;
                justify-content: center;
                margin-bottom: 32px;
            }
            
            .dropdown-wrapper {
                position: relative;
                min-width: 220px;
            }
            
            .Select-control {
                border-radius: 10px !important;
                border: 2px solid #e5e7eb !important;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05) !important;
                transition: all 0.3s ease !important;
            }
            
            .Select-control:hover {
                border-color: #667eea !important;
            }
            
            .medal-list {
                list-style: none;
                padding: 0;
            }
            
            .medal-item {
                background: linear-gradient(90deg, #f8fafc 0%, #f1f5f9 100%);
                padding: 12px 16px;
                margin-bottom: 8px;
                border-radius: 8px;
                border-left: 4px solid #667eea;
                font-size: 0.95rem;
                transition: all 0.3s ease;
            }
            
            .medal-item:hover {
                background: linear-gradient(90deg, #e2e8f0 0%, #cbd5e1 100%);
                transform: translateX(4px);
            }
            
            .medal-table {
                width: 100%;
                border-collapse: separate;
                border-spacing: 0;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
            }
            
            .medal-table th {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 16px 12px;
                font-weight: 600;
                text-align: left;
                font-size: 0.9rem;
            }
            
            .medal-table td {
                background: white;
                padding: 12px;
                border-bottom: 1px solid #f1f5f9;
                font-size: 0.9rem;
            }
            
            .medal-table tbody tr:hover {
                background: #f8fafc;
            }
            
            .medal-table tbody tr:last-child td {
                border-bottom: none;
            }
            
            .chart-container {
                background: white;
                border-radius: 16px;
                padding: 20px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                border: 1px solid rgba(0, 0, 0, 0.06);
                transition: all 0.3s ease;
            }
            
            .chart-container:hover {
                box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
            }
            
            .grid-2 {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 24px;
            }
            
            .grid-3 {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 20px;
            }
            
            .flex-row {
                display: flex;
                gap: 24px;
                align-items: stretch;
            }
            
            .flex-center {
                display: flex;
                justify-content: center;
                align-items: center;
                flex-wrap: wrap;
                gap: 16px;
            }
            
            .summary-text {
                font-size: 1.05rem;
                line-height: 1.6;
                color: #374151;
                margin-bottom: 20px;
                padding: 16px;
                background: linear-gradient(90deg, #f0f9ff 0%, #e0f2fe 100%);
                border-radius: 10px;
                border-left: 4px solid #0284c7;
            }
            
            @media (max-width: 768px) {
                .main-title {
                    font-size: 2rem;
                }
                
                .grid-2, .grid-3 {
                    grid-template-columns: 1fr;
                }
                
                .flex-row {
                    flex-direction: column;
                }
                
                .dashboard-container {
                    margin: 10px;
                    padding: 20px;
                }
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

app.layout = html.Div([
        # Header
        html.Div([
            html.Img(
                src="https://www.paralympicindia.com/_next/image?url=%2Fassets%2Flogo-lightbg.png&w=384&q=75",
                alt="Paralympic India Logo",
                style={
                    "height": "120px",
                    "marginBottom": "20px",
                    "objectFit": "contain"
                }
            ),
            html.H1("PCI Dashboard", className="main-title"),
            html.P("Paralympics Committee of India - Live Analytics", className="subtitle"),
            html.Hr(className="divider")
        ], className="header-section"),

        # Paralympics highlights
        html.Div([
            html.Div([
                html.H2([html.Span("🏆", className="icon"), "Daily Highlights"], 
                       className="section-title"),
                html.Div(id="event-summary"),
            ], className="section-card", style={"flex": "1.2"}),

            html.Div([
                html.H2([html.Span("🥇", className="icon"), "Medal Tally"], 
                       className="section-title"),
                html.Div(id="medal-tally"),
            ], className="section-card", style={"flex": "1"})
        ], className="flex-row", style={"marginBottom": "40px"}),

        # Cloudflare stats
        html.Div([
            html.H2([html.Span("🌐", className="icon"), "Cloudflare Analytics"], 
                   className="section-title", style={"textAlign": "center", "marginBottom": "30px"}),

            html.Div([
                html.Div([
                    dcc.Dropdown(
                        id="time-range",
                        options=[
                            {"label": "📅 Last 7 days", "value": 7},
                            {"label": "📅 Last 30 days", "value": 30},
                            {"label": "📅 Last 90 days", "value": 90},
                        ],
                        value=7,
                        clearable=False,
                        className="dropdown-select"
                    )
                ], className="dropdown-wrapper")
            ], className="dropdown-container"),

            html.Div(id="summary-cards", className="flex-center", 
                    style={"marginBottom": "40px"}),

            html.Div([
                html.Div([dcc.Graph(id="requests-graph")], className="chart-container"),
                html.Div([dcc.Graph(id="bandwidth-graph")], className="chart-container"),
                html.Div([dcc.Graph(id="threats-graph")], className="chart-container"),
            ], className="grid-3", style={"marginBottom": "40px"}),

            html.Div([
                html.Div([dcc.Graph(id="top-countries-bar")], className="chart-container"),
                html.Div([dcc.Graph(id="world-map")], className="chart-container"),
            ], className="grid-2")
        ], className="section-card"),

        dcc.Interval(id="interval", interval=5 * 60 * 1000, n_intervals=0)
    ], className="dashboard-container")


# ------------------------------
# CALLBACKS
# ------------------------------
@app.callback(
    [Output("event-summary", "children"),
     Output("medal-tally", "children")],
    Input("interval", "n_intervals")
)
def update_event_summary(n):
    raw = fetch_medallists()
    medals = parse_medallists(raw)
    stats = compute_medal_stats(medals)
    summary_msg = generate_medallist_summary(stats)
    medalist_msgs = generate_medalist_messages(stats["medallists"])

    # Medalist messages
    summary = html.Div([
        html.Div(summary_msg, className="summary-text"),
        html.Ul([
            html.Li(msg, className="medal-item") for msg in medalist_msgs
        ], className="medal-list")
    ])

    # Medal tally table
    tally_df = pd.DataFrame(stats["medal_tally"]).T.reset_index()
    tally_df = tally_df.rename(columns={"index": "Country"})
    table = html.Table([
        html.Thead(html.Tr([html.Th(col) for col in tally_df.columns])),
        html.Tbody([
            html.Tr([html.Td(tally_df.iloc[i][col]) for col in tally_df.columns])
            for i in range(len(tally_df))
        ])
    ], className="medal-table")

    return summary, table


@app.callback(
    [Output("summary-cards", "children"),
     Output("requests-graph", "figure"),
     Output("bandwidth-graph", "figure"),
     Output("threats-graph", "figure"),
     Output("top-countries-bar", "figure"),
     Output("world-map", "figure")],
    [Input("time-range", "value"),
     Input("interval", "n_intervals")]
)
def update_dashboard(days, n):
    df = fetch_timeseries(days)
    country_df = fetch_country_data(days)

    total_requests = df["requests"].sum()
    total_cached = df["cachedRequests"].sum()
    cache_ratio = (total_cached / total_requests * 100) if total_requests else 0
    total_bandwidth = df["bytes"].sum() / (1024**3)
    total_cached_bw = df["cachedBytes"].sum() / (1024**3)
    threats = df["threats"].sum()

    summary = [
        html.Div([
            html.Div(f"{total_requests:,}", className="stat-value"),
            html.Div("Total Requests", className="stat-label")
        ], className="stat-card"),
        html.Div([
            html.Div(f"{cache_ratio:.1f}%", className="stat-value"),
            html.Div("Cache Hit Ratio", className="stat-label")
        ], className="stat-card green"),
        html.Div([
            html.Div(f"{total_bandwidth:.2f} GB", className="stat-value"),
            html.Div("Total Bandwidth", className="stat-label")
        ], className="stat-card blue"),
        html.Div([
            html.Div(f"{threats:,}", className="stat-value"),
            html.Div("Threats Encountered and Blocked", className="stat-label")
        ], className="stat-card red"),
    ]

    # Enhanced chart styling
    chart_theme = dict(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", size=12, color="#374151"),
        title=dict(font=dict(size=16, weight=600, color="#1f2937")),
        margin=dict(l=40, r=40, t=60, b=40)
    )

    requests_fig = px.area(df, x="date", y=["requests", "cachedRequests"],
                           title="🔄 Requests Over Time",
                           labels={"value": "Requests", "date": "Date"},
                           color_discrete_sequence=['#667eea', '#764ba2'])
    requests_fig.update_layout(**chart_theme)

    bandwidth_fig = px.area(df, x="date", y=["bytes", "cachedBytes"],
                            title="📊 Bandwidth Over Time",
                            labels={"value": "Bytes", "date": "Date"},
                            color_discrete_sequence=['#10b981', '#059669'])
    bandwidth_fig.update_layout(**chart_theme)

    threats_fig = px.line(df, x="date", y="threats",
                          title="🛡️ Security Threats Over Time",
                          labels={"threats": "Threats", "date": "Date"},
                          color_discrete_sequence=['#ef4444'])
    threats_fig.update_layout(**chart_theme)
    threats_fig.update_traces(line=dict(width=3))

    bar_fig = px.bar(country_df.head(10), x="country", y="requests",
                     title="🌍 Top 10 Countries by Requests",
                     color="requests",
                     color_continuous_scale='Viridis')
    bar_fig.update_layout(**chart_theme)

    map_fig = px.choropleth(country_df, locations="iso_alpha3", color="requests",
                            title="🗺️ Global Request Distribution",
                            color_continuous_scale="Blues")
    map_fig.update_layout(**chart_theme)

    return summary, requests_fig, bandwidth_fig, threats_fig, bar_fig, map_fig


if __name__ == "__main__":
    app.run(debug=True, threaded=False, use_reloader=False, host='0.0.0.0', port=8050)