import os
import time
import json
import random
import requests
import torch
from datetime import datetime

GEMINI_API_KEY = "PLACEHOLDER_GEMINI"
GH_PAT = "PLACEHOLDER_GH_PAT"
GITHUB_REPO = "PLACEHOLDER_GITHUB_REPO"

print("📦 Installing dependencies...")
os.system("pip install -q moviepy==1.0.3 edge-tts diffusers transformers accelerate")

from moviepy.editor import VideoFileClip, concatenate_videoclips
from diffusers import DiffusionPipeline
from diffusers.utils import export_to_video

today_date = datetime.now().strftime("%d-%b-%Y")

print("🚀 Loading AI Video Model into T4 GPU...")
try:
    pipe = DiffusionPipeline.from_pretrained("damo-vilab/text-to-video-ms-1.7b", torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload()
    print("✅ Model Loaded Successfully!")
except Exception as e:
    print(f"❌ Model Load Error: {e}")
    exit(1)

def generate_local_gpu_video(prompt, filename):
    try:
        print(f"🎥 Generating (GPU): {prompt}")
        video_frames = pipe(prompt, num_frames=16).frames[0]
        export_to_video(video_frames, filename, fps=8)
        return True
    except Exception as e:
        print(f"❌ GPU Generation Error: {e}")
        return False

def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    headers = {"Content-Type": "application/json"}
    try:
        res = requests.post(url, json=payload, headers=headers)
        return res.json()['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return None

print("🔥 STARTING STABLE VIDEO GENERATION 🔥")
vid_num = int(time.time())

# Let's make a 35s Funny Snake Short first to test the full pipeline smoothly
topic = "Hilarious snake encounters in modern USA houses"
prompt = f"Write a 70-word USA English funny YouTube Shorts script about: {topic}. Output STRICTLY as JSON array of 3 objects: 1. 'narration': English line. 2. 'visual': 3-word visual prompt. RAW JSON ONLY."

script_txt = ask_gemini(prompt)
if not script_txt:
    print("❌ Failed to get Gemini script.")
    exit(1)

try:
    if script_txt.startswith("```json"): script_txt = script_txt[7:-3]
    scenes = json.loads(script_txt.strip())
except Exception as e:
    print(f"❌ JSON Parse Error: {e}")
    exit(1)

meta = ask_gemini(f"Generate for '{topic}': 1. Catchy Title (<60 chars) 2. 2-line Description 3. 5 tags. Format: TITLE|DESC|TAGS").split('|')
title, desc, tags = meta[0].strip(), meta[1].strip(), meta[2].strip()

clips = []
for i, scene in enumerate(scenes):
    raw_vid, aud_file, clip_file = f"raw_{vid_num}_{i}.mp4", f"aud_{vid_num}_{i}.mp3", f"clip_{vid_num}_{i}.mp4"
    os.system(f'edge-tts --voice "en-US-ChristopherNeural" --text "{scene["narration"]}" --write-media {aud_file}')
    
    if generate_local_gpu_video(scene["visual"], raw_vid):
        os.system(f'ffmpeg -y -stream_loop -1 -i "{raw_vid}" -i "{aud_file}" -map 0:v:0 -map 1:a:0 -c:v libx264 -c:a aac -shortest "{clip_file}" -loglevel error')
        clips.append(clip_file)

if clips:
    final_video = f"SHORT_USA_{vid_num}.mp4"
    clip_objs = [VideoFileClip(c) for c in clips]
    concatenate_videoclips(clip_objs).write_videofile(final_video, fps=24, codec="libx264", logger=None)
    
    new_entry = {"file": final_video, "title": title, "desc": desc, "tags": tags, "date": today_date, "id": str(vid_num), "cat": "SHORT", "status_msg": "🟢 100% Complete", "status_type": "done"}

    print("☁️ Pushing Video back to GitHub...")
    repo_url = f"https://oauth2:{GH_PAT}@[github.com/](https://github.com/){GITHUB_REPO}.git"
    os.system(f"git clone {repo_url} myrepo")
    
    history_file = "myrepo/history.json"
    history = []
    if os.path.exists(history_file):
        with open(history_file, "r") as f: history = json.loads(f.read())
        
    history.insert(0, new_entry)
    with open(history_file, "w") as f: f.write(json.dumps(history))
    
    os.system(f"cp {final_video} myrepo/")

    # Simple HTML generator
    html = """<!DOCTYPE html><html><head><title>🇺🇸 USA AI Studio</title><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #0f0f0f; color: #fff; margin: 0; padding: 20px; text-align: center; }
        h2 { color: #00e676; margin-top: 30px; border-bottom: 1px solid #333; padding-bottom: 5px;}
        .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .card { background: #1e1e1e; padding: 15px; border-radius: 10px; width: 320px; text-align: left; }
        video { width: 100%; border-radius: 8px; margin: 10px 0; }
        .btn { background: #00e676; color: #000; display: block; padding: 10px; text-align: center; text-decoration: none; font-weight: bold; border-radius: 5px; margin-bottom: 5px; cursor: pointer; border: none; width: 100%; }
        .btn-dark { background: #333; color: #fff; }
        .box { display: none; background: #111; padding: 10px; border-radius: 5px; margin-top: 5px; font-size: 13px; }
        .row { display: flex; justify-content: space-between; background: #222; margin-bottom: 5px; padding: 5px; border-radius: 3px; }
        .txt { flex: 1; overflow-x: auto; white-space: nowrap; margin-right: 10px; color: #ccc;}
        .cpy { background: #4285f4; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 11px;}
    </style></head><body><h1>🇺🇸 Automatic AI Studio</h1><h2>🐍 Funny Snake Shorts</h2><div class='grid'>"""

    for h in history:
        vid = h['id']
        html += f"""<div class="card"><b>📅 {h['date']}</b>
        <video src="{h['file']}" controls></video>
        <a href="{h['file']}" download class="btn">⬇️ Download</a>
        <button class="btn btn-dark" onclick="let b=document.getElementById('b-{vid}'); b.style.display = b.style.display==='block' ? 'none' : 'block'">📝 Title, Desc & Tags</button>
        <div class="box" id="b-{vid}">
            <div class="row"><div class="txt" id="t-{vid}">{h['title']}</div><button class="cpy" onclick="navigator.clipboard.writeText(document.getElementById('t-{vid}').innerText)">Copy</button></div>
            <div class="row"><div class="txt" id="d-{vid}">{h['desc']}</div><button class="cpy" onclick="navigator.clipboard.writeText(document.getElementById('d-{vid}').innerText)">Copy</button></div>
            <div class="row"><div class="txt" id="g-{vid}">{h['tags']}</div><button class="cpy" onclick="navigator.clipboard.writeText(document.getElementById('g-{vid}').innerText)">Copy</button></div>
        </div></div>"""

    html += "</div></body></html>"
    with open("myrepo/index.html", "w") as f: f.write(html)
    
    os.chdir("myrepo")
    os.system('git config user.name "Kaggle GPU Bot"')
    os.system('git config user.email "bot@kaggle.com"')
    os.system('git add .')
    os.system('git commit -m "Auto Update: Video Ready 🚀"')
    os.system('git push')
    print("✅ SUCCESS! Video and website pushed to GitHub.")
else:
    print("❌ No clips were generated.")
