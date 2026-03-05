from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import time

app = FastAPI()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8"><title>EVM Arb Ranker Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-black text-white p-4 md:p-8 font-sans">
    <div id="login" class="max-w-sm mx-auto mt-20 p-8 bg-zinc-900 rounded-2xl border border-zinc-800 text-center shadow-2xl">
        <h2 class="text-xl font-bold mb-6 uppercase">Admin Access</h2>
        <input id="u" type="text" placeholder="Username" class="w-full bg-black p-3 mb-3 border border-zinc-700 rounded-lg outline-none focus:border-blue-500">
        <input id="p" type="password" placeholder="Password" class="w-full bg-black p-3 mb-6 border border-zinc-700 outline-none focus:border-blue-500">
        <button id="unlock-btn" onclick="auth()" class="w-full bg-blue-600 py-3 rounded-lg font-black hover:bg-blue-500 uppercase text-xs tracking-widest">Unlock</button>
    </div>

    <div id="dash" class="hidden max-w-5xl mx-auto">
        <div class="flex justify-between items-center mb-10 bg-zinc-900 p-6 rounded-3xl border border-zinc-800">
             <div>
                <h1 class="text-2xl font-black text-blue-500 italic uppercase">EVM ARB RANKER</h1>
                <p class="text-[10px] text-zinc-500 font-bold uppercase">Live Scanner Active</p>
             </div>
             <div class="text-right">
                <p class="text-[10px] text-zinc-400 font-mono uppercase">samproeth</p>
                <button id="ref-btn" onclick="load()" class="text-[9px] bg-blue-600/20 text-blue-400 border border-blue-500/30 px-4 py-1.5 rounded-full mt-1 hover:bg-blue-600 hover:text-white transition-all font-bold">REFRESH SCANNER</button>
             </div>
        </div>
        <div id="results" class="grid grid-cols-1 gap-4"></div>
    </div>

    <script>
        function auth() {
            if(document.getElementById('u').value.trim() === 'samproeth' && document.getElementById('p').value.trim() === 'samproeth') {
                document.getElementById('login').style.display = 'none';
                document.getElementById('dash').classList.remove('hidden');
                load();
                setInterval(load, 45000);
            } else { alert("Wrong Login"); }
        }

        async function load() {
            const btn = document.getElementById('ref-btn');
            const container = document.getElementById('results');
            btn.innerHTML = "SCANNING CHAINS...";
            btn.disabled = true;

            try {
                const res = await fetch('/api/arbitrage');
                const data = await res.json();
                
                if(!data || data.length === 0) {
                    container.innerHTML = '<div class="text-center p-20 border border-dashed border-zinc-800 rounded-3xl text-zinc-600 text-[10px] uppercase tracking-widest font-bold">Scanning 5 Chains... No Spreads > 0.01% Found Right Now.</div>';
                } else {
                    container.innerHTML = data.map((item, i) => `
                        <div class="p-6 bg-zinc-900 rounded-2xl border border-zinc-800 flex flex-col md:flex-row justify-between items-center gap-6 hover:border-blue-500/50 transition-all">
                            <div class="w-full md:w-auto">
                                <span class="px-2 py-0.5 bg-blue-600 text-white text-[9px] font-black rounded uppercase">RANK #${i+1}</span>
                                <h3 class="text-2xl font-black mt-1">${item.symbol}</h3>
                                <p class="text-[9px] font-mono text-zinc-600 truncate max-w-[150px] uppercase">CA: ${item.ca}</p>
                            </div>
                            <div class="flex-1 flex justify-around items-center w-full px-4 text-center"><div><p class="text-[9px] text-zinc-500 font-bold uppercase mb-1">${item.buy.chain}</p><p class="text-emerald-400 font-mono font-bold">$${item.buy.price.toFixed(6)}</p></div>
                                <div class="text-zinc-700">➜</div>
                                <div><p class="text-[9px] text-zinc-500 font-bold uppercase mb-1">${item.sell.chain}</p><p class="text-blue-400 font-mono font-bold">$${item.sell.price.toFixed(6)}</p></div>
                            </div>
                            <div class="text-right w-full md:w-auto">
                                <p class="text-emerald-400 font-black text-3xl tabular-nums tracking-tighter">${item.spread}%</p>
                                <a href="${item.buy.link}" target="_blank" class="inline-block mt-2 bg-white text-black px-6 py-2 rounded-full font-black text-[10px] uppercase hover:bg-blue-600 hover:text-white transition-all">Open Pool</a>
                            </div>
                        </div>
                    `).join('');
                }
            } catch (e) { 
                container.innerHTML = '<div class="text-red-500 text-center font-mono text-xs p-10 uppercase">API Timeout - Retrying...</div>';
            } finally {
                btn.innerHTML = "REFRESH SCANNER";
                btn.disabled = false;
            }
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def read_root():
    return HTMLResponse(content=DASHBOARD_HTML)

# We use the top 4 most active chains to ensure the API responds within Vercel's time limit
CHAINS = ['eth', 'bsc', 'arbitrum', 'base']

@app.get("/api/arbitrage")
async def get_arb():
    all_opps = []
    groups = {}
    for chain in CHAINS:
        try:
            r = requests.get(f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools", 
                             headers={'Accept': 'application/json;version=20230203'}, timeout=2.0)
            data = r.json().get('data', [])
            for pool in data:
                attr = pool.get('attributes', {})
                # Lowered liquidity to $100 just to verify data is flowing
                if float(attr.get('reserve_in_usd', 0)) < 100: continue
                symbol = attr.get('symbol', '').split(' / ')[0]
                if not symbol: continue
                if symbol not in groups: groups[symbol] = []
                groups[symbol].append({
                    "price": float(attr.get('token_price_usd', 0)),
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
        # Show even tiny spreads so you can see the dashboard is working
        if spread > 0.001:
            all_opps.append({"symbol": sym, "spread": round(spread, 3), "ca": low['ca'], "buy": low, "sell": high})
            
    return sorted(all_opps, key=lambda x: x['spread'], reverse=True)
