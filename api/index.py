from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import time

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

EVM_CHAINS = ['eth', 'bsc', 'arbitrum', 'polygon_pos', 'base', 'optimism', 'avax']

@app.get("/api/arbitrage")
def get_arb():
    all_opps = []
    groups = {}
    
    for chain in EVM_CHAINS:
        try:
            r = requests.get(f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools", 
                             headers={'Accept': 'application/json;version=20230203'}, timeout=5)
            data = r.json().get('data', [])
            for pool in data:
                attr = pool['attributes']
                if float(attr.get('reserve_in_usd', 0)) < 1000: continue
                
                symbol = attr['symbol'].split(' / ')[0]
                if symbol not in groups: groups[symbol] = []
                groups[symbol].append({
                    "price": float(attr['token_price_usd']),
                    "dex": pool['relationships']['dex']['data']['id'].upper(),
                    "chain": chain.upper(),
                    "ca": pool['relationships']['base_token']['data']['id'].split('_')[-1],
                    "link": f"https://www.geckoterminal.com/{chain}/pools/{attr['address']}"
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
