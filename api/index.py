from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

# We put the HTML directly in the variable to avoid all file-path errors
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8"><title>EVM Arb Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-black text-white p-6 font-sans">
    <div id="login" class="max-w-sm mx-auto mt-20 p-8 bg-zinc-900 rounded-xl border border-zinc-800 text-center">
        <h2 class="text-xl font-bold mb-4">ADMIN ACCESS</h2>
        <input id="u" type="text" placeholder="User" class="w-full bg-black p-2 mb-2 border border-zinc-700 outline-none rounded">
        <input id="p" type="password" placeholder="Pass" class="w-full bg-black p-2 mb-4 border border-zinc-700 outline-none rounded">
        <button onclick="auth()" class="w-full bg-blue-600 py-2 rounded font-bold hover:bg-blue-500 transition-all">UNLOCK</button>
    </div>

    <div id="dash" class="hidden max-w-4xl mx-auto">
        <h1 class="text-2xl font-black text-blue-500 italic mb-8">EVM ARB RANKER</h1>
        <div id="results" class="grid grid-cols-1 gap-4"></div>
    </div>

    <script>
        function auth() {
            if(document.getElementById('u').value === 'samproeth' && document.getElementById('p').value === 'samproeth') {
                document.getElementById('login').classList.add('hidden');
                document.getElementById('dash').classList.remove('hidden');
                load();
                setInterval(load, 30000);
            } else { alert("Invalid login"); }
        }
        async function load() {
            try {
                const res = await fetch('/api/arbitrage');
                const data = await res.json();
                document.getElementById('results').innerHTML = data.map((item, i) => 
                    <div class="p-5 bg-zinc-900 rounded-xl border border-zinc-800 flex justify-between items-center">
                        <div>
                            <p class="text-[10px] text-zinc-500 font-bold">RANK #${i+1}</p>
                            <h3 class="text-xl font-bold text-white">${item.symbol}</h3>
                            <p class="text-[9px] font-mono text-zinc-600 truncate max-w-[150px]">${item.ca}</p>
                        </div>
                        <div class="text-right">
                            <p class="text-emerald-400 font-black text-2xl">${item.spread}%</p>
                            <p class="text-[10px] text-zinc-500 mb-2">${item.buy.chain} ➜ ${item.sell.chain}</p>
                            <a href="${item.buy.link}" target="_blank" class="bg-white text-black text-[10px] px-3 py-1 rounded font-black uppercase hover:bg-blue-500 hover:text-white transition-all">GO TO POOL</a>
                        </div>
                    </div>
                ).join('');
            } catch (e) { console.error("API Error", e); }
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def read_root():
    return HTMLResponse(content=DASHBOARD_HTML)

EVM_CHAINS = ['eth', 'bsc', 'arbitrum', 'polygon_pos', 'base', 'optimism', 'avax']

@app.get("/api/arbitrage")
async def get_arb():
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
                if symbol not in groups: groups[symbol] = []groups[symbol].append({
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
            all_opps.append({"symbol": sym, "spread": round(spread, 2), "ca": low['ca'], "buy": low, "sell": high})
            
    return sorted(all_opps, key=lambda x: x['spread'], reverse=True)
