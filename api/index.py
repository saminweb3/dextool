from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

# Integrated UI and Logic to bypass all file-path errors
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EVM Arb Ranker Pro</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-black text-white p-4 md:p-8 font-sans">
    <div id="login" class="max-w-sm mx-auto mt-20 p-8 bg-zinc-900 rounded-2xl border border-zinc-800 text-center shadow-2xl">
        <h2 class="text-xl font-bold mb-6 tracking-tighter uppercase">Admin Access</h2>
        <input id="u" type="text" placeholder="Username" class="w-full bg-black p-3 mb-3 border border-zinc-700 rounded-lg outline-none focus:border-blue-500 transition-all">
        <input id="p" type="password" placeholder="Password" class="w-full bg-black p-3 mb-6 border border-zinc-700 rounded-lg outline-none focus:border-blue-500 transition-all">
        <button id="unlock-btn" onclick="auth()" class="w-full bg-blue-600 py-3 rounded-lg font-black hover:bg-blue-500 transition-all uppercase text-xs tracking-widest">Unlock</button>
    </div>

    <div id="dash" class="hidden max-w-5xl mx-auto">
        <div class="flex justify-between items-center mb-10 bg-zinc-900 p-6 rounded-3xl border border-zinc-800">
             <div>
                <h1 class="text-2xl font-black text-blue-500 italic tracking-tighter uppercase">EVM ARB RANKER</h1>
                <p class="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Live DEX Spread Scanner</p>
             </div>
             <div class="text-right">
                <p class="text-[10px] text-zinc-400 font-mono uppercase">Session: samproeth</p>
                <button onclick="load()" class="text-[9px] bg-zinc-800 px-3 py-1 rounded mt-1 hover:bg-zinc-700">Refresh Now</button>
             </div>
        </div>
        
        <div id="results" class="grid grid-cols-1 gap-4">
            <div class="text-center p-20 text-zinc-600 animate-pulse font-mono text-xs uppercase italic">
                Scanning EVM Chains... Please Wait
            </div>
        </div>
    </div>

    <script>
        function auth() {
            const user = document.getElementById('u').value.trim();
            const pass = document.getElementById('p').value.trim();
            
            if(user === 'samproeth' && pass === 'samproeth') {
                document.getElementById('login').style.display = 'none';
                document.getElementById('dash').classList.remove('hidden');
                load();
                setInterval(load, 30000); // Auto-refresh every 30 seconds
            } else { 
                alert("Invalid Credentials."); 
            }
        }

        async function load() {
            const container = document.getElementById('results');
            try {
                const res = await fetch('/api/arbitrage');
                const data = await res.json();
                
                if(!data || data.length === 0) {
                    container.innerHTML = '<div class="text-center p-10 border border-zinc-800 rounded-2xl text-zinc-500 text-[10px] uppercase tracking-widest">Scanning 5 Chains... No Spreads > 0.01% Found Yet</div>';
                    return;
                }

                container.innerHTML = data.map((item, i) => `
                    <div class="p-6 bg-zinc-900 rounded-2xl border ${i===0?'border-yellow-500/50 shadow-lg':'border-zinc-800'} flex flex-col md:flex-row justify-between items-center gap-6 hover:bg-zinc-800/50 transition-all">
                        <div class="w-full md:w-auto">
                            <span class="px-2 py-0.5 ${i===0?'bg-yellow-500 text-black':'bg-zinc-800 text-zinc-400'} text-[10px] font-black rounded uppercase">RANK #${i+1}</span><h3 class="text-2xl font-bold tracking-tighter mt-1">${item.symbol}</h3>
                            <p class="text-[9px] font-mono text-zinc-600 truncate max-w-[200px] mt-1 uppercase">CA: ${item.ca}</p>
                        </div>

                        <div class="flex-1 flex justify-around items-center w-full px-4 text-center">
                            <div>
                                <p class="text-[9px] text-zinc-500 font-bold uppercase mb-1">${item.buy.chain}</p>
                                <p class="text-emerald-400 font-mono font-bold">$${item.buy.price.toFixed(6)}</p>
                            </div>
                            <div class="text-zinc-700">➜</div>
                            <div>
                                <p class="text-[9px] text-zinc-500 font-bold uppercase mb-1">${item.sell.chain}</p>
                                <p class="text-blue-400 font-mono font-bold">$${item.sell.price.toFixed(6)}</p>
                            </div>
                        </div>

                        <div class="text-right w-full md:w-auto">
                            <p class="text-emerald-400 font-black text-3xl tabular-nums tracking-tighter">${item.spread}%</p>
                            <a href="${item.buy.link}" target="_blank" class="inline-block mt-2 bg-white text-black px-6 py-2 rounded-full font-black text-[10px] uppercase hover:bg-blue-500 hover:text-white transition-all">Trade Now</a>
                        </div>
                    </div>
                `).join('');
            } catch (e) { 
                container.innerHTML = '<div class="text-red-500 p-4 text-center font-mono text-xs uppercase">API Timeout: Retrying...</div>';
            }
        }
    </script>
</body>
</html>
"""

@app.get("/")
async def read_root():
    return HTMLResponse(content=DASHBOARD_HTML)

# Optimized chain list to fit within Vercel's 10-second limit
CHAINS = ['eth', 'bsc', 'arbitrum', 'base', 'polygon_pos']

@app.get("/api/arbitrage")
async def get_arb():
    all_opps = []
    groups = {}
    
    for chain in CHAINS:
        try:
            # Short timeout to ensure the function returns before Vercel kills it
            r = requests.get(
                f"https://api.geckoterminal.com/api/v2/networks/{chain}/trending_pools", 
                headers={'Accept': 'application/json;version=20230203'}, 
                timeout=2.5
            )
            if r.status_code != 200: continue
            
            data = r.json().get('data', [])
            for pool in data:
                attr = pool.get('attributes', {})
                # Lowered liquidity filter ($500) to find more results
                if float(attr.get('reserve_in_usd', 0)) < 500: continue
                
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
    
    for sym, pools in groups.items():
        if len(pools) < 2: continue
        pools.sort(key=lambda x: x['price'])
        low, high = pools[0], pools[-1]
        
        if low['price'] <= 0: continue
        spread = ((high['price'] - low['price']) / low['price']) * 100
        
        # Show all spreads above 0.01% for real-time visibility
        if spread > 0.01:
            all_opps.append({
                "symbol": sym, "spread": round(spread, 2), "ca": low['ca'], "buy": low, "sell": high
            })
            
    return sorted(all_opps, key=lambda x: x['spread'], reverse=True)
