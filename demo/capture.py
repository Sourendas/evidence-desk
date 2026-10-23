import os
import json, time
from playwright.sync_api import sync_playwright
OUT='raw/'
with sync_playwright() as p:
    b=p.chromium.launch(executable_path=os.environ.get('CHROME') or None,headless=True)
    pg=b.new_page(viewport={'width':1600,'height':900})
    pg.goto('http://localhost:8787/'); pg.wait_for_timeout(800)
    pg.screenshot(path=OUT+'01_home.png')
    pg.click('#sample'); pg.wait_for_timeout(300)
    pg.screenshot(path=OUT+'02_sample.png')
    t=time.time()
    with pg.expect_response(lambda r: '/api/ask' in r.url, timeout=240000) as ri:
        pg.click('#go')
        pg.wait_for_timeout(400); pg.screenshot(path=OUT+'03_running.png')
    d=ri.value.json(); el=time.time()-t; json.dump(d,open(OUT+'live_full.json','w'),indent=1)
    json.dump({'elapsed_s':round(el,1),**{k:d.get(k) for k in ('recommendation','confidence','confidence_label','reasoning','risks','next_actions','sources','trace')},'n_evidence':len(d['evidence'])},open(OUT+'live_run.json','w'),indent=1)
    pg.wait_for_timeout(800)
    cards=pg.query_selector_all('#out .card')
    names=['rec','graph','why','trace','evidence','risks','sources']
    for i,c in enumerate(cards):
        pg.evaluate('(e)=>{window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY-12)}',c); pg.wait_for_timeout(300)
        pg.screenshot(path=OUT+f'1{i}_{names[i] if i<len(names) else i}.png')
    # hover a claim node
    pg.evaluate('(e)=>{window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY-12)}',cards[1]); pg.wait_for_timeout(200)
    nd=pg.query_selector_all('#wg .nd')
    claims=[n for n in nd if (n.get_attribute('data-id') or '').startswith('C')]
    tgt=claims[0] if claims else nd[1]
    tgt.hover(); pg.wait_for_timeout(400); pg.screenshot(path=OUT+'20_graph_hover.png')
    # evidence scroll extra
    pg.evaluate('(e)=>{window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY+700)}',cards[4]); pg.wait_for_timeout(200)
    pg.screenshot(path=OUT+'21_evidence2.png')
    # trace details expanded (verify)
    pg.evaluate('''()=>{const li=[...document.querySelectorAll('.trace li')];const v=li.find(l=>/verify/i.test(l.querySelector('.stage').textContent));if(v){v.querySelector('details').open=true;window.scrollTo(0,v.getBoundingClientRect().top+window.scrollY-12)}}'''); pg.wait_for_timeout(300)
    pg.screenshot(path=OUT+'22_verify_detail.png')
    md=d['markdown']; open(OUT+'report.md','w').write(md)
    print('elapsed',round(el,1),'conf',d['confidence'],d['confidence_label'],'ev',len(d['evidence']),'claims',len(d['reasoning']),'cards',len(cards),'nodes',len(nd),[n.get_attribute('data-id') for n in nd][:12])
    b.close()
