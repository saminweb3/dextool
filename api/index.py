from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

# Simple HTML fallback in case the file is missing
DEFAULT_HTML = "<html><body><h1>Dashboard Loading...</h1><script>window.location.reload()</script></body></html>"

@app.get("/")
async def read_index():
    # Standard Vercel path logic
    path = os.path.join(os.getcwd(), "public", "index.html")
    if os.path.exists(path):
        with open(path, "r") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content=DEFAULT_HTML)

@app.get("/api/arbitrage")
async def get_arb():
    # Only use basic chains for initial stability
    chains = ['eth', 'bsc', 'arbitrum', 'base']
    all_opps = []
    
    for chain in chains:
        try:
            url = f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools"
            r = requests.get(url, headers={'Accept': 'application/json;version=20230203'}, timeout=5)
            data = r.json().get('data', [])
            
            # Simplified logic for speed and stability
            for pool in data:
                attr = pool.get('attributes', {})
                liq = float(attr.get('reserve_in_usd', 0))
                if liq < 1000: continue
                
                all_opps.append({
                    "symbol": attr.get('symbol', 'Unknown').split(' / ')[0],
                    "spread": 1.5, # Placeholder for fast testing
                    "ca": pool['relationships']['base_token']['data']['id'].split('_')[-1],
                    "buy": {"chain": chain.upper(), "price": float(attr.get('token_price_usd', 0)), "dex": "DEX", "link": "#"}
                })
        except:
            continue
            
    return all_opps
