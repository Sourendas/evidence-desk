import os
import html
from playwright.sync_api import sync_playwright
CSS="""*{margin:0;box-sizing:border-box}body{width:1600px;height:900px;font-family:'DejaVu Sans',system-ui,sans-serif;color:#e8eaf6;
background:radial-gradient(circle at 15% 15%,#26285a 0,#11132a 45%,#0b0d1a 100%);padding:110px 120px;overflow:hidden}
h1{font-size:92px;font-weight:800;letter-spacing:-1px}h1 span{color:#7c9cff}h2{font-size:64px;font-weight:800;margin-bottom:26px}
.sub{font-size:34px;color:#c6cbef;margin-top:22px;line-height:1.35}.tag{display:inline-block;margin-top:46px;font-size:24px;padding:10px 20px;border:1px solid #4b56a8;border-radius:30px;color:#aab4ff}
ul{margin-top:34px;list-style:none}li{font-size:30px;margin:20px 0;padding-left:40px;position:relative;line-height:1.35}li:before{content:'';position:absolute;left:4px;top:13px;width:14px;height:14px;border-radius:50%;background:#7c6cff}
.flow{display:flex;gap:16px;margin-top:40px;flex-wrap:wrap}.st{background:#1b1e3d;border:1px solid #3d4590;border-radius:14px;padding:18px 22px;font-size:26px;min-width:190px}.st b{display:block;color:#7c9cff;font-size:20px;margin-bottom:6px}
.small{font-size:24px;color:#9aa0c3;margin-top:30px;line-height:1.5}pre{font:18px/1.36 'DejaVu Sans Mono',monospace;background:#05060d;border:1px solid #2b2f55;border-radius:12px;padding:24px 28px;color:#b8f5c4;white-space:pre-wrap}
.ok{color:#5ee08a}"""
def page(body): return f"<html><head><style>{CSS}</style></head><body>{body}</body></html>"
tests=open('raw/tests.txt').read().replace('GET /\nGET /api/health\nPOST /api/ask\n','')
lines=[l.split(' (')[0]+' ... ok' if l.endswith('ok') else l for l in tests.splitlines()]
S={
'00_title':page("<h1>Evidence <span>Desk</span></h1><div class='sub'>The agent that can explain why.<br>Every claim traces back to a verbatim, verified quote.</div><div class='tag'>Open Agent Hackathon 2026 · Track 02 — The Agent That Can Explain Why</div>"),
'01_problem':page("<h2>The problem</h2><div class='sub'>AI answers sound confident, but you can't check them.</div><ul><li>Citations get invented; quotes get paraphrased into things nobody said</li><li>The reasoning is hidden, so you can't tell which fact drove the answer</li><li>Real decisions (bid on this job? enter this contest?) need a visible <b>why</b></li></ul>"),
'30_how':page("<h2>How it works</h2><div class='flow'><div class='st'><b>1 · PLAN</b>sub-questions</div><div class='st'><b>2 · RETRIEVE</b>snippets · URLs · Wikipedia</div><div class='st'><b>3 · EXTRACT</b>BM25 verbatim quotes</div><div class='st'><b>4 · SYNTHESIZE</b>claims cite E-ids</div><div class='st'><b>5 · VERIFY</b>drop fake ids · verbatim check</div><div class='st'><b>6 · CONCLUDE</b>report + why-graph</div></div><ul><li>Stdlib-only Python agent, no framework, no paid services</li><li>LLM: NVIDIA Nemotron 3 Nano (30B-A3B) via Nebius Token Factory, OpenAI-compatible API</li><li>No key? Deterministic stub mode, fully usable offline</li></ul>"),
't1_tests':page("<h2 style='font-size:44px'>22 tests, no network, no key</h2><pre>$ python -m unittest discover -s tests -t . -v\n"+html.escape("\n".join([l for l in lines if l.startswith("test_")]+["","Ran 22 tests in 0.54s","","OK"])).replace('... ok',"... <span class='ok'>ok</span>")+"</pre>"),
'40_close':page("<h1>Evidence <span>Desk</span></h1><div class='sub'>Answers you can check.</div><ul><li>Sponsor slots ready: Zetaris source adapter · Meterless usage meter (not yet connected)</li><li>Open source, MIT: github.com/Sourendas/evidence-desk</li></ul><div class='tag'>Thanks for watching</div>"),
}
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=os.environ.get('CHROME') or None,headless=True)
    pg=b.new_page(viewport={'width':1600,'height':900})
    for k,v in S.items():
        pg.set_content(v); pg.wait_for_timeout(150); pg.screenshot(path=f'raw/{k}.png')
    b.close()
