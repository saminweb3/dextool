from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import requests
import os

app = FastAPI()

# Enable CORS so the frontend can communicate with the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base directory logic to handle Vercel's file structure
# This points to the /api folder where this script lives
BASE_DIR = os.path.dirname(os.path.abspath(file))

@app.get("/")
async def read_index():
    """
    Serves the index.html from the /public folder.
    The path logic goes up one level from /api to root, then into /public.
    """
    path = os.path.join(BASE_DIR, "..", "public", "index.html")
    
    if os.path.exists(path):
        return FileResponse(path)
    
    # Debugging info if the file is missing
    return {
        "error": "index.html not found", 
        "expected_path": path,
        "current_dir_contents": os.listdir(BASE_DIR)
    }

EVM_CHAINS = ['eth', 'bsc', 'arbitrum', 'polygon_pos', 'base', 'optimism', 'avax']

@app.get("/api/arbitrage")
async def get_arb():
    """
    Fetches trending pools across EVM chains and calculates spreads.
    """
    all_opps = []
    groups = {}
    
    for chain in EVM_CHAINS:
        try:
            # Using the GeckoTerminal V2 API
            r = requests.get(
                f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools", 
                headers={'Accept': 'application/json;version=20230203'}, 
                timeout=10
            )
            if r.status_code != 200:
                continue
                
            data = r.json().get('data', [])
            for pool in data:
                attr = pool.get('attributes', {})
                liq = float(attr.get('reserve_in_usd', 0))
                
                # Filter: $1,000 Minimum Liquidity
                if liq < 1000: 
                    continue
                
                symbol = attr.get('symbol', '').split(' / ')[0]
                if not symbol:
                    continue
                    
                if symbol not in groups: 
                    groups[symbol] = []
                
                groups[symbol].append({
                    "price": float(attr.get('token_price_usd', 0)),
                    "dex": pool['relationships']['dex']['data']['id'].upper(),
                    "chain": chain.upper(),
                    "ca": pool['relationships']['base_token']['data']['id'].split('_')[-1],
                    "link": f"https://www.geckoterminal.com/{chain}/pools/{attr.get('address')}"
                })
        except Exception: 
            continue

    # Calculate spreads and rank opportunities
    for sym, pools in groups.items():
        if len(pools) < 2: 
            continue
            
        pools.sort(key=lambda x: x['price'])
        low, high = pools[0], pools[-1]
        
        if low['price'] <= 0:
            continue
            
        spread = ((high['price'] - low['price']) / low['price']) * 100
        
        # Only include opportunities with a positive spread
        if spread > 0.01:
            all_opps.append({
                "symbol": sym, 
                "spread": round(spread, 2), 
                "ca": low['ca'],
                "buy": low, 
                "sell": high
            })

    # Sort by Rank (Highest Spread first)
    return sorted(all_opps, key=lambda x: x['spread'], reverse=True)
