import os
from playwright.sync_api import sync_playwright
import base64
img=base64.b64encode(open('raw/11_graph.png','rb').read()).decode()
H=f"""<html><body style="margin:0;width:1500px;height:1000px;overflow:hidden;font-family:'DejaVu Sans',sans-serif;color:#e8eaf6;
background:radial-gradient(circle at 15% 10%,#2a2d66 0,#11132a 50%,#0b0d1a 100%)">
<div style="padding:70px 80px 0"><div style="font-size:88px;font-weight:800">Evidence <span style="color:#7c9cff">Desk</span></div>
<div style="font-size:36px;color:#c6cbef;margin-top:14px">The agent that can explain why — every claim traced to a verified quote</div>
<div style="display:inline-block;margin-top:24px;font-size:22px;padding:8px 18px;border:1px solid #4b56a8;border-radius:28px;color:#aab4ff">Open Agent Hackathon 2026 · Track 02 · NVIDIA Nemotron</div></div>
<div style="position:absolute;left:80px;top:390px;width:1340px;height:560px;border-radius:18px;overflow:hidden;border:1px solid #3d4590;box-shadow:0 20px 60px #0008;
background:url(data:image/png;base64,{img}) no-repeat;background-size:1900px auto;background-position:-560px -10px"></div></body></html>"""
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=os.environ.get('CHROME') or None,headless=True)
    pg=b.new_page(viewport={'width':1500,'height':1000}); pg.set_content(H); pg.wait_for_timeout(300)
    pg.screenshot(path='../cover.png'); b.close()
