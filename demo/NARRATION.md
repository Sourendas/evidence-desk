# Evidence Desk demo — narration script

Video: `evidence_desk_demo_voice.mp4` (1280x720, 30 fps, H.264 + AAC). Frames are real headless-Chrome screenshots of the local app (`python server.py`) during one live run with NVIDIA Nemotron 3 Nano 30B-A3B on Nebius Token Factory (key loaded from a private env file, never shown), plus title/explainer slides. Raw API response: `raw/live_full.json`.

TTS: edge-tts en-US-AndrewNeural (free, no account or key), rate +0%, no speed-up. Each scene holds for its narration + 0.9 s (0.4 s lead-in). Loudness normalized with ffmpeg loudnorm (I=-16 LUFS). Voice only, no music. Rebuild: `python capture.py` (needs server running), `python slides.py`, `python build.py`.

| # | Start | Hold (s) | Speech (s) | Frame | Narration |
|---|---|---|---|---|---|
| 1 | 0:00.00 | 11.8 | 10.9 | 00_title.png | This is Evidence Desk, for the Open Agent Hackathon, track two: the agent that can explain why. Every claim in its answer traces back to a verbatim, verified quote. |
| 2 | 0:11.84 | 12.6 | 11.7 | 01_problem.png | Most AI answers sound confident, but you can't check them. Citations get invented, and the reasoning stays hidden. For a real decision, like whether to bid on a freelance job, you need to see why. |
| 3 | 0:24.43 | 15.9 | 15.0 | 02_sample.png | Here's Evidence Desk running locally, in live mode, with NVIDIA Nemotron 3 Nano. We load a sample: a freelance job post for an n8n workflow, a short profile of the freelancer, and the n8n Wikipedia page. |
| 4 | 0:40.33 | 7.5 | 6.6 | 03_running.png | We click Investigate. The agent plans sub-questions, retrieves the sources, and extracts evidence. |
| 5 | 0:47.78 | 14.7 | 13.8 | 10_rec.png | About thirteen seconds later, we get the recommendation: yes, consider bidding, but mind the tight deadline and the competition, and showcase relevant n8n experience. Confidence is 0.89, high. |
| 6 | 1:02.46 | 14.4 | 13.5 | 11_graph.png | This is the why-graph. It reads left to right: the recommendation, the seven claims behind it, the verbatim quotes each claim cites, and the sources those quotes came from. Green edges support, red edges caution. |
| 7 | 1:16.82 | 9.9 | 9.0 | 20_graph_hover.png | Hover any node, and only its path lights up. This claim, about the job scope, rests on three quotes, all from the pasted job post. |
| 8 | 1:26.77 | 12.5 | 11.6 | 13_trace.png | The explain-why trace lists every step, with timings. Extract ranked forty-one sentences with BM25, and picked fifteen quotes from three sources, with no duplicates. |
| 9 | 1:39.26 | 16.1 | 15.2 | 22_verify_detail.png | The verify step is the safety net. A claim that cites evidence which doesn't exist is dropped, and every quote is re-checked, word for word, against its source. Here, seven of seven claims were kept, and fifteen of fifteen quotes verified. |
| 10 | 1:55.33 | 9.8 | 9.0 | 14_evidence.png | Each quote shows its source, the sub-question it answers, its ranking score, and the matched terms. So even the choice of evidence is explainable. |
| 11 | 2:05.18 | 9.2 | 8.3 | 15_risks.png | Then come open risks and next actions. The whole result exports as a markdown report, with the why-graph as a Mermaid diagram. |
| 12 | 2:14.41 | 16.3 | 15.4 | 30_how.png | Under the hood, it's a plain Python agent with no framework and no paid services. The model is NVIDIA Nemotron, through Nebius Token Factory's OpenAI compatible API. Without a key, a deterministic stub keeps it usable offline. |
| 13 | 2:30.74 | 9.3 | 8.4 | t1_tests.png | Twenty-two tests cover quote ranking, the citation verifier, the why-graph, and the server, and they run with no network and no key. |
| 14 | 2:40.09 | 13.0 | 12.1 | 40_close.png | Adapter slots for Zetaris data and Meterless metering are ready, though not connected yet. Evidence Desk: answers you can check. It's open source, under the MIT license. Thanks for watching. |

Total: 2:53.26 (173.3 s)
