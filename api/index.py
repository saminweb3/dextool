from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

@app.get("/")
async def read_index():
    # This is the most reliable way to find your file on Vercel
    # It looks exactly for the 'public' folder in your root
    current_dir = os.path.dirname(os.path.abspath(file))
    path = os.path.join(current_dir, "..", "public", "index.html")
    
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            # If the file is missing, we show exactly where the server looked
            return HTMLResponse(f"<h1>File Not Found</h1><p>Looked in: {path}</p>")
    except Exception as e:
        return HTMLResponse(f"<h1>Server Error</h1><p>{str(e)}</p>")

@app.get("/api/arbitrage")
async def get_arb():
    # Keep your existing scanner logic here
    # (Fetching from GeckoTerminal and ranking by spread)
    return {"status": "logic_active"}
