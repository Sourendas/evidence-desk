import subprocess, json, os
VOICE='en-US-AndrewNeural'
SC=[
('00_title.png',"This is Evidence Desk, for the Open Agent Hackathon, track two: the agent that can explain why. Every claim in its answer traces back to a verbatim, verified quote."),
('01_problem.png',"Most AI answers sound confident, but you can't check them. Citations get invented, and the reasoning stays hidden. For a real decision, like whether to bid on a freelance job, you need to see why."),
('02_sample.png',"Here's Evidence Desk running locally, in live mode, with NVIDIA Nemotron 3 Nano. We load a sample: a freelance job post for an n8n workflow, a short profile of the freelancer, and the n8n Wikipedia page."),
('03_running.png',"We click Investigate. The agent plans sub-questions, retrieves the sources, and extracts evidence."),
('10_rec.png',"About thirteen seconds later, we get the recommendation: yes, consider bidding, but mind the tight deadline and the competition, and showcase relevant n8n experience. Confidence is 0.89, high."),
('11_graph.png',"This is the why-graph. It reads left to right: the recommendation, the seven claims behind it, the verbatim quotes each claim cites, and the sources those quotes came from. Green edges support, red edges caution."),
('20_graph_hover.png',"Hover any node, and only its path lights up. This claim, about the job scope, rests on three quotes, all from the pasted job post."),
('13_trace.png',"The explain-why trace lists every step, with timings. Extract ranked forty-one sentences with BM25, and picked fifteen quotes from three sources, with no duplicates."),
('22_verify_detail.png',"The verify step is the safety net. A claim that cites evidence which doesn't exist is dropped, and every quote is re-checked, word for word, against its source. Here, seven of seven claims were kept, and fifteen of fifteen quotes verified."),
('14_evidence.png',"Each quote shows its source, the sub-question it answers, its ranking score, and the matched terms. So even the choice of evidence is explainable."),
('15_risks.png',"Then come open risks and next actions. The whole result exports as a markdown report, with the why-graph as a Mermaid diagram."),
('30_how.png',"Under the hood, it's a plain Python agent with no framework and no paid services. The model is NVIDIA Nemotron, through Nebius Token Factory's OpenAI compatible API. Without a key, a deterministic stub keeps it usable offline."),
('t1_tests.png',"Twenty-two tests cover quote ranking, the citation verifier, the why-graph, and the server, and they run with no network and no key."),
('40_close.png',"Adapter slots for Zetaris data and Meterless metering are ready, though not connected yet. Evidence Desk: answers you can check. It's open source, under the MIT license. Thanks for watching."),
]
os.makedirs('composed',exist_ok=True); os.makedirs('build',exist_ok=True)
rows=[];t=0.0;segs=[]
def dur(f): return float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]).decode())
for i,(fr,txt) in enumerate(SC):
    a=f'build/a{i:02d}.mp3'
    import time
    for k in range(5):
        r=subprocess.run([os.environ.get('EDGE_TTS','edge-tts'),'--voice',VOICE,'--text',txt,'--write-media',a],capture_output=True,text=True)
        if r.returncode==0 and os.path.getsize(a)>1000: break
        print('tts retry',i,r.stderr.strip().splitlines()[-1:] ); time.sleep(5+5*k)
    else: raise SystemExit('tts failed')
    sp=dur(a); hold=round(sp+0.9,2)
    subprocess.run(['ffmpeg','-y','-v','error','-i',f'raw/{fr}','-vf','scale=1280:720:flags=lanczos',f'composed/{fr}'],check=True)
    seg=f'build/s{i:02d}.mp4'
    subprocess.run(['ffmpeg','-y','-v','error','-loop','1','-framerate','30','-t',str(hold),'-i',f'composed/{fr}','-i',a,
      '-filter_complex','[1:a]adelay=400|400,apad,atrim=0:%s,aresample=48000,aformat=channel_layouts=stereo[a]'%hold,
      '-map','0:v','-map','[a]','-c:v','libx264','-pix_fmt','yuv420p','-preset','medium','-crf','20','-tune','stillimage','-r','30','-c:a','aac','-b:a','160k','-t',str(hold),seg],check=True)
    segs.append(seg); rows.append((i+1,t,hold,sp,fr,txt)); t+=hold
open('build/list.txt','w').write(''.join(f"file '{os.path.basename(s)}'\n" for s in segs))
subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i','build/list.txt','-c','copy','build/concat.mp4'],check=True)
subprocess.run(['ffmpeg','-y','-v','error','-i','build/concat.mp4','-c:v','copy','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:a','aac','-b:a','160k','-movflags','+faststart','evidence_desk_demo_voice.mp4'],check=True)
total=dur('evidence_desk_demo_voice.mp4')
fmt=lambda s:f"{int(s//60)}:{s%60:05.2f}"
md=["# Evidence Desk demo — narration script","",
"Video: `evidence_desk_demo_voice.mp4` (1280x720, 30 fps, H.264 + AAC). Frames are real headless-Chrome screenshots of the local app (`python server.py`) during one live run with NVIDIA Nemotron 3 Nano 30B-A3B on Nebius Token Factory (key loaded from a private env file, never shown), plus title/explainer slides. Raw API response: `raw/live_full.json`.","",
f"TTS: edge-tts {VOICE} (free, no account or key), rate +0%, no speed-up. Each scene holds for its narration + 0.9 s (0.4 s lead-in). Loudness normalized with ffmpeg loudnorm (I=-16 LUFS). Voice only, no music. Rebuild: `python capture.py` (needs server running), `python slides.py`, `python build.py`.","",
"| # | Start | Hold (s) | Speech (s) | Frame | Narration |","|---|---|---|---|---|---|"]
for n,s,h,sp,fr,txt in rows: md.append(f"| {n} | {fmt(s)} | {h:.1f} | {sp:.1f} | {fr} | {txt} |")
md+=["",f"Total: {fmt(total)} ({total:.1f} s)"]
open('NARRATION.md','w').write("\n".join(md)+"\n")
print('total',total)
