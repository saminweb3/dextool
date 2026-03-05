from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

# Enable CORS for frontend-backend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def read_index():
    """
    Search for index.html in all possible Vercel deployment paths.
    This prevents the infinite 'Dashboard Loading' loop.
    """
    # 1. Define all possible locations for the public folder
    paths_to_try = [
        os.path.join(os.getcwd(), "public", "index.html"),
        os.path.join(os.path.dirname(os.path.dirname(file)), "public", "index.html"),
        os.path.join(os.path.dirname(file), "..", "public", "index.html"),
        "/var/task/public/index.html"
    ]
    
    # 2. Try to find and return the file
    for path in paths_to_try:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return HTMLResponse(content=f.read())
            except Exception as e:
                return HTMLResponse(content=f"<h1>Read Error</h1><p>{str(e)}</p>")

    # 3. If no file is found, show a debug map instead of looping
    debug_info = f"""
    <h1>File Not Found</h1>
    <p>The server could not find <b>public/index.html</b>.</p>
    <hr>
    <b>Paths checked:</b><br>
    <ul style="font-family:monospace;">
        {"".join([f"<li>{p}</li>" for p in paths_to_try])}
    </ul>
    <b>Current Directory:</b> {os.getcwd()}<br>
    <b>Directory Contents:</b> {os.listdir(os.getcwd())}
    """
    return HTMLResponse(content=debug_info)

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
            r = requests.get(
                f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools", 
                headers={'Accept': 'application/json;version=20230203'}, 
                timeout=8
            )
            if r.status_code != 200: continue
                
            data = r.json().get('data', [])
            for pool in data:
                attr = pool.get('attributes', {})
                liq = float(attr.get('reserve_in_usd', 0))
                
                # Filter: $1,000 Minimum Liquidity
                if liq < 1000: continue
                
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
        
        if low['price'] <= 0: continue
        spread = ((high['price'] - low['price']) / low['price']) * 100
        
        if spread > 0.1:
            all_opps.append({
                "symbol": sym, 
                "spread": round(spread, 2), 
                "ca": low['ca'],
                "buy": low, 
                "sell": high
            })

    return sorted(all_opps, key=lambda x: x['spread'], reverse=True)
