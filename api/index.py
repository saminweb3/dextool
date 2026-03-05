from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests

app = FastAPI()

# This variable holds your entire website UI and JavaScript
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EVM Arb Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-black text-white p-6 font-sans">
    <div id="login" class="max-w-sm mx-auto mt-20 p-8 bg-zinc-900 rounded-xl border border-zinc-800 text-center shadow-2xl">
        <h2 class="text-xl font-bold mb-6 tracking-tighter uppercase">Admin Access</h2>
        <input id="u" type="text" placeholder="Username" class="w-full bg-black p-3 mb-3 border border-zinc-700 outline-none rounded-lg focus:border-blue-500 transition-all">
        <input id="p" type="password" placeholder="Password" class="w-full bg-black p-3 mb-6 border border-zinc-700 outline-none rounded-lg focus:border-blue-500 transition-all">
        <button id="unlock-btn" onclick="auth()" class="w-full bg-blue-600 py-3 rounded-lg font-black hover:bg-blue-500 transition-all uppercase text-xs tracking-widest">Unlock</button>
    </div>

    <div id="dash" class="hidden max-w-4xl mx-auto">
        <div class="flex justify-between items-center mb-8 bg-zinc-900 p-6 rounded-2xl border border-zinc-800">
             <h1 class="text-2xl font-black text-blue-500 italic">EVM ARB RANKER</h1>
             <div class="text-right"><p class="text-[10px] text-zinc-500 font-bold uppercase">Session: samproeth</p></div>
        </div>
        <div id="results" class="grid grid-cols-1 gap-4">
            <div class="text-center p-10 text-zinc-600 animate-pulse font-mono text-xs uppercase italic">
                Initializing Scanner...
            </div>
        </div>
    </div>

    <script>
        function auth() {
            // .trim() removes any accidental spaces before or after the text
            const user = document.getElementById('u').value.trim();
            const pass = document.getElementById('p').value.trim();
            const btn = document.getElementById('unlock-btn');
            
            // Credentials you requested: samproeth / samproeth
            if(user === 'samproeth' && pass === 'samproeth') {
                btn.innerHTML = "LOADING...";
                document.getElementById('login').style.display = 'none';
                document.getElementById('dash').classList.remove('hidden');
                load();
                setInterval(load, 45000); // Auto-update data every 45 seconds
            } else { 
                alert("Access Denied: Please check your credentials."); 
            }
        }

        async function load() {
            try {
                const res = await fetch('/api/arbitrage');
                const data = await res.json();
                
                if(!data || data.length === 0) {
                    document.getElementById('results').innerHTML = '<div class="text-center p-10 border border-zinc-800 rounded-xl text-zinc-500 text-xs uppercase">No Spreads Found - Scanning Chains...</div>';
                    return;
                }

                document.getElementById('results').innerHTML = data.map((item, i) => `
                    <div class="p-5 bg-zinc-900 rounded-xl border border-zinc-800 flex justify-between items-center hover:border-zinc-600 transition-all">
                        <div>
                            <p class="text-[10px] text-zinc-500 font-bold mb-1 uppercase tracking-tighter">Rank #${i+1}</p>
                            <h3 class="text-xl font-black tracking-tighter">${item.symbol}</h3>
                            <p class="text-[9px] font-mono text-zinc-600 truncate max-w-[150px] uppercase">CA: ${item.ca}</p></div>
                        <div class="text-right">
                            <p class="text-emerald-400 font-black text-3xl tabular-nums tracking-tighter">${item.spread}%</p>
                            <p class="text-[9px] text-zinc-500 font-bold uppercase mb-2">${item.buy.chain} ➜ ${item.sell.chain}</p>
                            <a href="${item.buy.link}" target="_blank" class="bg-white text-black text-[10px] px-4 py-1.5 rounded-full font-black uppercase hover:bg-blue-600 hover:text-white transition-all shadow-lg">Trade</a>
                        </div>
                    </div>
                `).join('');
            } catch (e) { 
                console.error("API Error:", e);
                document.getElementById('results').innerHTML = '<div class="text-red-500 p-4 text-center font-mono text-xs uppercase">Server Connection Error</div>';
            }
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def read_root():
    # Returns the HTML UI directly from the Python variable
    return HTMLResponse(content=DASHBOARD_HTML)

# Supported EVM Chains for Scanning
EVM_CHAINS = ['eth', 'bsc', 'arbitrum', 'polygon_pos', 'base', 'optimism', 'avax']

@app.get("/api/arbitrage")
async def get_arb():
    all_opps = []
    groups = {}
    
    for chain in EVM_CHAINS:
        try:
            # Fetch data from GeckoTerminal
            r = requests.get(
                f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools", 
                headers={'Accept': 'application/json;version=20230203'}, 
                timeout=5
            )
            if r.status_code != 200: continue
            
            data = r.json().get('data', [])
            for pool in data:
                attr = pool.get('attributes', {})
                # Minimum Liquidity Check ($1,000)
                if float(attr.get('reserve_in_usd', 0)) < 1000: continue
                
                symbol = attr.get('symbol', '').split(' / ')[0]
                if not symbol: continue
                
                if symbol not in groups: groups[symbol] = []
                groups[symbol].append({
                    "price": float(attr.get('token_price_usd', 0)),
                    "chain": chain.upper(),
                    "ca": pool['relationships']['base_token']['data']['id'].split('_')[-1],
                    "link": f"https://www.geckoterminal.com/{chain}/pools/{attr.get('address')}"
                })
        except: 
            continue
    
    # Calculate spreads between different DEXs/Chains
    for sym, pools in groups.items():
        if len(pools) < 2: continue
        pools.sort(key=lambda x: x['price'])
        low, high = pools[0], pools[-1]
        
        if low['price'] <= 0: continue
        spread = ((high['price'] - low['price']) / low['price']) * 100
        
        # Only show spreads higher than 0.1%
        if spread > 0.1:
            all_opps.append({
                "symbol": sym, 
                "spread": round(spread, 2), 
                "ca": low['ca'], 
                "buy": low, 
                "sell": high
            })
            
    return sorted(all_opps, key=lambda x: x['spread'], reverse=True)
