from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

# This is the UI content
html_content = """
<!DOCTYPE html>
<html>
<head><title>EVM Arb Pro</title><script src="https://cdn.tailwindcss.com"></script></head>
<body class="bg-black text-white p-6 font-sans text-center">
    <div id="login" class="max-w-sm mx-auto mt-20 p-8 bg-zinc-900 rounded-xl border border-zinc-800">
        <h2 class="text-xl font-bold mb-4 uppercase">Admin Access</h2>
        <input id="u" type="text" placeholder="User" class="w-full bg-black p-2 mb-2 border border-zinc-700 outline-none rounded">
        <input id="p" type="password" placeholder="Pass" class="w-full bg-black p-2 mb-4 border border-zinc-700 outline-none rounded">
        <button onclick="auth()" class="w-full bg-blue-600 py-2 rounded font-bold uppercase">Unlock</button>
    </div>
    <div id="dash" class="hidden max-w-4xl mx-auto text-left">
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
            } else { alert("Wrong Login"); }
        }
        async function load() {
            try {
                const res = await fetch('/api/arbitrage');
                const data = await res.json();
                document.getElementById('results').innerHTML = data.map((item, i) => 
                    <div class="p-5 bg-zinc-900 rounded-xl border border-zinc-800 flex justify-between items-center">
                        <div>
                            <p class="text-[10px] text-zinc-500 font-bold uppercase">Rank #${i+1}</p>
                            <h3 class="text-xl font-bold text-white">${item.symbol}</h3>
                            <p class="text-[9px] font-mono text-zinc-600 uppercase">${item.ca}</p>
                        </div>
                        <div class="text-right">
                            <p class="text-emerald-400 font-black text-2xl">${item.spread}%</p>
                            <a href="${item.buy.link}" target="_blank" class="bg-white text-black text-[10px] px-3 py-1 rounded font-black uppercase">Trade</a>
                        </div>
                    </div>
                ).join('');
            } catch (e) { console.error(e); }
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def home():
    return HTMLResponse(content=html_content)

@app.get("/api/arbitrage")
async def scan():
    # Supports core EVM chains
    chains = ['eth', 'bsc', 'arbitrum', 'base', 'polygon_pos']
    all_opps = []
    groups = {}
    for chain in chains:
        try:
            url = f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools"
            r = requests.get(url, headers={'Accept': 'application/json;version=20230203'}, timeout=5)
            data = r.json().get('data', [])
            for pool in data:
                attr = pool.get('attributes', {})
                if float(attr.get('reserve_in_usd', 0)) < 1000: continue
                symbol = attr.get('symbol', '').split(' / ')[0]
                if not symbol: continue
                if symbol not in groups: groups[symbol] = []
                groups[symbol].append({
                    "price": float(attr.get('token_price_usd', 0)),
                    "chain": chain.upper(),
                    "ca": pool['relationships']['base_token']['data']['id'].split('_')[-1],"link": f"https://www.geckoterminal.com/{chain}/pools/{attr.get('address')}"
                })
        except: continue
    for sym, pools in groups.items():
        if len(pools) < 2: continue
        pools.sort(key=lambda x: x['price'])
        low, high = pools[0], pools[-1]
        spread = ((high['price'] - low['price']) / low['price']) * 100
        if spread > 0.1:
            all_opps.append({"symbol": sym, "spread": round(spread, 2), "ca": low['ca'], "buy": low})
    return sorted(all_opps, key=lambda x: x['spread'], reverse=True)
