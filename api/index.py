from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_index():
    # Attempt to find index.html using relative paths Vercel prefers
    # This avoids the 'Internal Server Error' caused by absolute path failures
    possible_paths = [
        os.path.join(os.getcwd(), "public", "index.html"),
        os.path.join(os.path.dirname(file), "..", "public", "index.html"),
        "/var/task/public/index.html"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    
    # Debug message if file is still not found
    return HTMLResponse(f"<h1>Configuration Error</h1><p>Could not find index.html. Current Dir: {os.getcwd()}</p>")

EVM_CHAINS = ['eth', 'bsc', 'arbitrum', 'polygon_pos', 'base', 'optimism', 'avax']

@app.get("/api/arbitrage")
async def get_arb():
    all_opps = []
    groups = {}
    
    for chain in EVM_CHAINS:
        try:
            r = requests.get(
                f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools", 
                headers={'Accept': 'application/json;version=20230203'}, 
                timeout=5
            )
            if r.status_code != 200: continue
            data = r.json().get('data', [])
            for pool in data:
                attr = pool.get('attributes', {})
                if float(attr.get('reserve_in_usd', 0)) < 1000: continue
                
                symbol = attr.get('symbol', '').split(' / ')[0]
                if not symbol: continue
                if symbol not in groups: groups[symbol] = []
                
                groups[symbol].append({
                    "price": float(attr.get('token_price_usd', 0)),
                    "dex": pool['relationships']['dex']['data']['id'].upper(),
                    "chain": chain.upper(),
                    "ca": pool['relationships']['base_token']['data']['id'].split('_')[-1],
                    "link": f"https://www.geckoterminal.com/{chain}/pools/{attr.get('address')}"
                })
        except: continue

    for sym, pools in groups.items():
        if len(pools) < 2: continue
        pools.sort(key=lambda x: x['price'])
        low, high = pools[0], pools[-1]
        spread = ((high['price'] - low['price']) / low['price']) * 100
        
        if spread > 0.1:
            all_opps.append({
                "symbol": sym, "spread": round(spread, 2), "ca": low['ca'],
                "buy": low, "sell": high
            })

    return sorted(all_opps, key=lambda x: x['spread'], reverse=True)
