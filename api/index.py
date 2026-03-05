from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
import os

app = FastAPI()

def find_html():
    """Search for index.html in common Vercel locations."""
    # List of possible locations for public/index.html
    possible_locations = [
        os.path.join(os.getcwd(), "public", "index.html"),
        os.path.join(os.path.dirname(os.path.dirname(file)), "public", "index.html"),
        os.path.join(os.path.dirname(file), "..", "public", "index.html"),
        "/var/task/public/index.html"
    ]
    
    for path in possible_locations:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
    return None

@app.get("/")
async def read_index():
    content = find_html()
    if content:
        return HTMLResponse(content=content)
    
    # If the file is NOT found, we show a debug screen instead of crashing
    return HTMLResponse(f"""
        <body style="background:black;color:white;font-family:sans-serif;padding:50px;">
            <h1 style="color:#ef4444;">File Connection Error</h1>
            <p>The Python server is alive, but it cannot find <b>public/index.html</b>.</p>
            <p><b>Current Folder:</b> {os.getcwd()}</p>
            <p><b>Folders Found:</b> {os.listdir(os.getcwd())}</p>
        </body>
    """)

@app.get("/api/arbitrage")
async def get_arb():
    # Keep your scanner logic here
    return [{"symbol": "BTC/ETH", "spread": 1.2, "status": "active"}]
