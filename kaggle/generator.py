import os
import time
import json
import requests
import torch
import random
import shlex  # 👈 New import to fix the edge-tts text error!
from datetime import datetime

# GitHub will automatically replace these placeholders when running!
GEMINI_API_KEY = "PLACEHOLDER_GEMINI"
GH_PAT = "PLACEHOLDER_GH_PAT"
GITHUB_REPO = "PLACEHOLDER_GITHUB_REPO"

print("📦 Installing locked dependencies for the ultimate stable 3D Video generator...")
os.system("pip install -q diffusers==0.30.2 transformers==4.44.2 accelerate imageio-ffmpeg moviepy==1.0.3 edge-tts")

from moviepy.editor import VideoFileClip, concatenate_videoclips
from diffusers import CogVideoXPipeline
from diffusers.utils import export_to_video

today_date = datetime.now().strftime("%d-%b-%Y")
day_of_year = datetime.now().timetuple().tm_yday

print("🚀 Loading CogVideoX-2B (Premium 3D AI Model) into T4 GPU...")
try:
    pipe = CogVideoXPipeline.from_pretrained("THUDM/CogVideoX-2b", torch_dtype=torch.float16)
    pipe.enable_model_cpu_offload() 
    pipe.vae.enable_slicing()
    pipe.vae.enable_tiling()
    print("✅ 3D Model Loaded Successfully!")
except Exception as e:
    print(f"❌ Model Load Error: {e}")
    exit(1)

def generate_local_gpu_video(prompt, filename):
    try:
        hd_prompt = f"3d pixar style animation, vibrant colors, highly detailed, realistic textures, smooth cinematic motion, {prompt}"
        print(f"🎥 Generating 3D Video: {hd_prompt}")
        
        video_frames = pipe(prompt=hd_prompt, num_frames=49, num_inference_steps=25).frames[0]
        export_to_video(video_frames, filename, fps=8)
        return True
    except Exception as e:
        print(f"❌ GPU Generation Error: {e}")
        return False

def ask_gemini(prompt):
    print("🧠 Contacting Gemini AI...")
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": GEMINI_API_KEY
    }
    payload = {
        "model": "gemini-3.6-flash",
        "input": [{"type": "user_input", "content": [{"type": "text", "text": prompt}]}],
        "store": False
    }
    try:
        res = requests.post(url, json=payload, headers=headers)
        data = res.json()
        text_output = ""
        if data and "steps" in data:
            for step in data["steps"]:
                if step.get("type") == "model_output":
                    for item in step.get("content", []):
                        if item.get("type") == "text": text_output += item.get("text", "")
        return text_output.strip() if text_output else None
    except Exception as e:
        print(f"❌ Gemini Error: {e}")
        return None

print("🔥 STARTING ULTIMATE USA VIDEO GENERATION 🔥")
vid_num = int(time.time())

if day_of_year % 2 == 0:
    cat = "LONG"
    topics = [
        "A 3D animated magical forest camping adventure with cute animals and glowing crystals",
        "A touching 3D story about a poor boy working hard and transforming his life in a beautiful USA town",
        "A magical 3D journey through a hidden valley filled with exotic colorful birds and waterfalls"
    ]
    topic = random.choice(topics)
    prompt = f"Write a 90-word USA English 3D animated movie script about: {topic}. Output STRICTLY as JSON with 2 keys: 1. 'narration': The full English story text (Keep sentences very short). 2. 'visual': A 10-word description for a single, highly detailed 3D scene that represents the whole story. RAW JSON ONLY."
else:
    cat = "SHORT"
    topics = [
        "Funny 3D animated inverse reality where a human bites a snake in bed and the snake screams for a hospital",
        "Hilarious 3D animated cartoon snakes getting scared of a crying human in a deep jungle hole",
        "Funny 3D animated inverse reality where snakes drink tea at a stall and get scared of a human running towards them"
    ]
    topic = random.choice(topics)
    prompt = f"Write a 40-word USA English funny 3D cartoon shorts script about: {topic}. Output STRICTLY as JSON with 2 keys: 1. 'narration': The full English script (Keep sentences short and funny). 2. 'visual': A 10-word description for a single, highly detailed 3D scene. RAW JSON ONLY."

script_txt = ask_gemini(prompt)
if not script_txt:
    print("❌ Failed to get Gemini script.")
    exit(1)

try:
    if script_txt.startswith("```json"): script_txt = script_txt[7:-3]
    elif script_txt.startswith("```"): script_txt = script_txt[3:-3]
    scene_data = json.loads(script_txt.strip())
except Exception as e:
    print(f"❌ JSON Parse Error: {e}\nRaw text: {script_txt}")
    exit(1)

meta_raw = ask_gemini(f"Generate for '{topic}': 1. Catchy YouTube Title (<60 chars) 2. 2-line Description 3. 5 comma-separated tags. Format: TITLE|DESC|TAGS")
if meta_raw:
    meta = meta_raw.split('|')
    title = meta[0].strip() if len(meta) > 0 else "Amazing 3D Animation! 🌟"
    desc = meta[1].strip() if len(meta) > 1 else "Must watch 3D animated viral short! #shorts"
    tags = meta[2].strip() if len(meta) > 2 else "3d, animation, viral, usa, shorts"
else:
    title, desc, tags = "Amazing 3D Adventure! 🌟", "Must watch! #shorts", "3d, animation, viral"

raw_vid, aud_file, final_video = f"raw_{vid_num}.mp4", f"aud_{vid_num}.mp3", f"{cat}_USA_{vid_num}.mp4"

# 🚀 The FIX: Use shlex.quote to safely pass the text to the Linux command line!
safe_text = shlex.quote(scene_data["narration"])
os.system(f'edge-tts --voice "en-US-ChristopherNeural" --text {safe_text} --write-media {aud_file}')

if generate_local_gpu_video(scene_data["visual"], raw_vid):
    cmd = f'ffmpeg -y -i "{raw_vid}" -i "{aud_file}" -map 0:v:0 -map 1:a:0 -vf "tpad=stop_mode=clone:stop_duration=20" -c:v libx264 -c:a aac -shortest -loglevel error "{final_video}"'
    os.system(cmd)
    
    print("☁️ Cloning GitHub Repo & Pushing Files...")
    repo_url = f"https://oauth2:{GH_PAT}@github.com/{GITHUB_REPO}.git"
    os.system(f"git clone {repo_url} myrepo")
    
    history_file = "myrepo/history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f: history = json.loads(f.read())
        except: pass
        
    new_entry = {"file": final_video, "title": title, "desc": desc, "tags": tags, "date": today_date, "id": str(vid_num), "cat": cat, "status_msg": "🟢 HD 3D Masterpiece", "status_type": "done"}
    history.insert(0, new_entry)
    
    with open(history_file, "w") as f: f.write(json.dumps(history))
    os.system(f"cp {final_video} myrepo/")

    html = """<!DOCTYPE html><html lang="en"><head><title>🇺🇸 USA 3D AI Studio</title><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #0b0b0b; color: #fff; margin: 0; padding: 20px; text-align: center; }
        h1 { color: #ffeb3b; font-size: 24px; margin-bottom: 5px; }
        p { color: #aaa; font-size: 14px; margin-top: 0; }
        h2 { color: #00e676; margin-top: 30px; border-bottom: 2px solid #222; padding-bottom: 8px; font-size: 18px; text-align: left; }
        .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .card { background: #181818; padding: 15px; border-radius: 12px; width: 320px; border: 1px solid #333; text-align: left; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .date { font-size: 11px; color: #00e676; margin-bottom: 8px; font-weight: bold; }
        video { width: 100%; border-radius: 8px; background: #000; margin-bottom: 10px; cursor: pointer; }
        .btn { background: #00e676; color: #000; display: block; padding: 10px; text-align: center; text-decoration: none; font-weight: bold; border-radius: 6px; margin-bottom: 8px; cursor: pointer; border: none; width: 100%; box-sizing: border-box; }
        .btn-dark { background: #2a2a2a; color: #fff; font-size: 13px; }
        .box { display: none; background: #111; padding: 10px; border-radius: 8px; margin-top: 8px; font-size: 12px; border: 1px solid #333; }
        .row { display: flex; align-items: center; background: #1a1a1a; margin-bottom: 6px; border-radius: 4px; overflow: hidden; border: 1px solid #333; }
        .txt { flex: 1; padding: 8px; color: #ddd; overflow-x: auto; white-space: nowrap; font-family: monospace; }
        .cpy { background: #4285f4; color: white; border: none; padding: 8px 12px; cursor: pointer; font-weight: bold; font-size: 11px; }
        .cpy:hover { background: #3367d6; }
    </style></head>
    <body>
        <h1>🇺🇸 USA 3D Animation Studio</h1>
        <p>High-Quality 3D Videos - Fully Automated</p>
    """

    for cat_key, cat_name in [("LONG", "🎬 Epic 3D Stories (Long)"), ("SHORT", "🐍 3D Inverse Reality & Snake Shorts")]:
        html += f"<h2>{cat_name}</h2><div class='grid'>"
        cat_items = [h for h in history if h.get('cat') == cat_key]
        if not cat_items:
            html += "<p style='color:#555; font-size:13px;'>Generating next batch soon...</p>"
        for h in cat_items:
            vid = h['id']
            html += f"""<div class="card">
                <div class="date">📅 {h['date']}</div>
                <video src="{h['file']}" controls preload="none" poster=""></video>
                <a href="{h['file']}" download class="btn">⬇️ Download Video</a>
                <button class="btn btn-dark" onclick="let b=document.getElementById('b-{vid}'); b.style.display = b.style.display==='block' ? 'none' : 'block'">📝 Title, Desc & Tags</button>
                <div class="box" id="b-{vid}">
                    <div style="font-size:10px; color:#888; margin-bottom:2px;">TITLE:</div>
                    <div class="row"><div class="txt" id="t-{vid}">{h['title']}</div><button class="cpy" onclick="navigator.clipboard.writeText(document.getElementById('t-{vid}').innerText)">COPY</button></div>
                    <div style="font-size:10px; color:#888; margin-bottom:2px;">DESCRIPTION:</div>
                    <div class="row"><div class="txt" id="d-{vid}">{h['desc']}</div><button class="cpy" onclick="navigator.clipboard.writeText(document.getElementById('d-{vid}').innerText)">COPY</button></div>
                    <div style="font-size:10px; color:#888; margin-bottom:2px;">TAGS:</div>
                    <div class="row"><div class="txt" id="g-{vid}">{h['tags']}</div><button class="cpy" onclick="navigator.clipboard.writeText(document.getElementById('g-{vid}').innerText)">COPY</button></div>
                </div>
            </div>"""
        html += "</div>"

    html += "</body></html>"
    with open("myrepo/index.html", "w") as f: f.write(html)
    
    os.chdir("myrepo")
    os.system('git config user.name "Kaggle GPU Bot"')
    os.system('git config user.email "bot@kaggle.com"')
    os.system('git add .')
    os.system('git commit -m "Auto Update: HQ 3D Video Ready 🚀"')
    os.system('git push origin main || git push origin master')
    print("✅ SUCCESS! Perfect Quality 3D Video pushed to GitHub.")
else:
    print("❌ No clips were generated.")