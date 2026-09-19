import os
import time
import json
import requests
import torch
import random
import shlex
import gc
from datetime import datetime

GEMINI_API_KEY = "PLACEHOLDER_GEMINI"
GH_PAT = "PLACEHOLDER_GH_PAT"
GITHUB_REPO = "PLACEHOLDER_GITHUB_REPO"

print("📦 Installing locked dependencies for the memory-safe Image-to-Video 5B setup...")
os.system("pip install -q git+https://github.com/huggingface/diffusers.git transformers==4.44.2 accelerate imageio-ffmpeg moviepy==1.0.3 edge-tts")

from moviepy.editor import VideoFileClip, concatenate_videoclips
from diffusers import AutoPipelineForText2Image, CogVideoXImageToVideoPipeline
from diffusers.utils import export_to_video, load_image

today_date = datetime.now().strftime("%d-%b-%Y")

def ask_gemini(prompt):
    print("🧠 Contacting Gemini AI...")
    url = "https://generativelanguage.googleapis.com/v1beta/interactions"
    headers = {"Content-Type": "application/json", "x-goog-api-key": GEMINI_API_KEY}
    payload = {"model": "gemini-3.6-flash", "input": [{"type": "user_input", "content": [{"type": "text", "text": prompt}]}], "store": False}
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

print("🔥 STARTING 5B-I2V ULTIMATE USA VIDEO GENERATION 🔥")
vid_num = int(time.time())

master_prompt = '''You are an AUTOMATIC YouTube Shorts Funny Snake Video Creator.
Create a completely original funny 3D animated video.
Language: USA English. Style: High-quality funny 3D cartoon animation.

Randomly choose a fresh concept. Sometimes set it in a deep jungle, sometimes in a human environment. 

YOU MUST assign suitable expressive American voices from this list:
- en-US-GuyNeural (Excited male)
- en-US-AriaNeural (Energetic female)
- en-US-SteffanNeural (Deep strong male)
- en-US-JennyNeural (Natural female)

Output STRICTLY as a JSON array of objects for 3 scenes.
Each object MUST have:
1. "voice": EXACT name of the voice.
2. "narration": Short, funny English dialogue.
3. "visual": Detailed 3D scene description.
RAW JSON ARRAY ONLY.'''

script_txt = ask_gemini(master_prompt)
if not script_txt: exit(1)

try:
    if script_txt.startswith("```json"): script_txt = script_txt[7:-3]
    elif script_txt.startswith("```"): script_txt = script_txt[3:-3]
    scenes = json.loads(script_txt.strip())
except Exception as e:
    exit(1)

meta_raw = ask_gemini(f"Based on this script: {script_txt}. Generate: 1. Catchy Title (<60 chars) 2. 2-line Description 3. 5 tags. Format: TITLE|DESC|TAGS")
if meta_raw and '|' in meta_raw:
    meta = meta_raw.split('|')
    title, desc, tags = meta[0].strip(), meta[1].strip() if len(meta) > 1 else "Must watch!", meta[2].strip() if len(meta) > 2 else "3d, animation"
else:
    title, desc, tags = "Amazing 3D Adventure! 🌟", "Must watch! #shorts", "3d, animation, viral"

# ==========================================
# STAGE 1: GENERATE ALL IMAGES FIRST
# ==========================================
print("🎨 STAGE 1: Loading SDXL Turbo to generate reference images...")
img_pipe = AutoPipelineForText2Image.from_pretrained("stabilityai/sdxl-turbo", torch_dtype=torch.float16, variant="fp16")
img_pipe.enable_model_cpu_offload()

for i, scene in enumerate(scenes):
    print(f"🖼️ Generating image for scene {i+1}...")
    image_prompt = f"Highly detailed 3D Pixar style animation frame, masterpiece, best quality, vibrant colors, {scene['visual']}"
    reference_image = img_pipe(prompt=image_prompt, num_inference_steps=4, guidance_scale=0.0).images[0]
    img_path = f"ref_{vid_num}_{i}.png"
    reference_image.save(img_path)
    scene['img_path'] = img_path

# Completely obliterate the image model from memory
del img_pipe
gc.collect()
torch.cuda.empty_cache()
print("✅ Images generated and SDXL completely cleared from VRAM!")

# ==========================================
# STAGE 2: GENERATE ALL VIDEOS
# ==========================================
print("🚀 STAGE 2: Loading CogVideoX-5B-I2V to animate images...")
try:
    # BUG FIX: Added variant="fp16" so it doesn't crush the Kaggle CPU RAM!
    video_pipe = CogVideoXImageToVideoPipeline.from_pretrained(
        "THUDM/CogVideoX-5b-I2V", 
        torch_dtype=torch.float16,
        variant="fp16" 
    )
    # Using sequential offload saves maximum VRAM for 5B model on Kaggle T4
    video_pipe.enable_sequential_cpu_offload()
    video_pipe.vae.enable_slicing()
    video_pipe.vae.enable_tiling()
except Exception as e:
    print(f"❌ 5B Model Load Error: {e}")
    exit(1)

clips = []
for i, scene in enumerate(scenes):
    raw_vid = f"raw_{vid_num}_{i}.mp4"
    aud_file = f"aud_{vid_num}_{i}.mp3"
    clip_file = f"clip_{vid_num}_{i}.mp4"
    
    print(f"🎙️ Generating audio and video for scene {i+1}...")
    voice = scene.get("voice", "en-US-GuyNeural")
    safe_text = shlex.quote(scene["narration"])
    os.system(f'edge-tts --voice "{voice}" --rate=+15% --text {safe_text} --write-media {aud_file}')
    
    try:
        ref_image = load_image(scene['img_path'])
        video_prompt = f"Smooth cinematic motion, clear focus, high quality 3d animation, {scene['visual']}"
        video_frames = video_pipe(image=ref_image, prompt=video_prompt, num_frames=49, num_inference_steps=25).frames[0]
        export_to_video(video_frames, raw_vid, fps=12)
        
        # Ultra-smooth FFmpeg sync
        cmd = f'ffmpeg -y -i "{raw_vid}" -i "{aud_file}" -map 0:v:0 -map 1:a:0 -vf "tpad=stop_mode=clone:stop_duration=10, fps=24" -c:v libx264 -preset fast -crf 18 -c:a aac -shortest -loglevel error "{clip_file}"'
        os.system(cmd)
        clips.append(clip_file)
    except Exception as e:
        print(f"❌ Video Generation Error on scene {i+1}: {e}")

# Free video memory
del video_pipe
gc.collect()
torch.cuda.empty_cache()

# ==========================================
# STAGE 3: STITCH AND PUSH
# ==========================================
if clips:
    final_video = f"USA_3D_SHORT_{vid_num}.mp4"
    clip_objs = [VideoFileClip(c) for c in clips]
    concatenate_videoclips(clip_objs).write_videofile(final_video, fps=24, codec="libx264", logger=None)
    
    print("☁️ Pushing to GitHub...")
    repo_url = f"https://oauth2:{GH_PAT}@github.com/{GITHUB_REPO}.git"
    os.system(f"git clone {repo_url} myrepo")
    
    history_file = "myrepo/history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r") as f: history = json.loads(f.read())
        except: pass
        
    history.insert(0, {"file": final_video, "title": title, "desc": desc, "tags": tags, "date": today_date, "id": str(vid_num), "cat": "SHORT"})
    with open(history_file, "w") as f: f.write(json.dumps(history))
    os.system(f"cp {final_video} myrepo/")

    html = """<!DOCTYPE html><html lang="en"><head><title>🇺🇸 USA 3D AI Studio</title><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: sans-serif; background: #0b0b0b; color: #fff; margin: 0; padding: 20px; text-align: center; }
        h1 { color: #ffeb3b; font-size: 24px; margin-bottom: 5px; }
        h2 { color: #00e676; margin-top: 30px; border-bottom: 2px solid #222; padding-bottom: 8px; font-size: 18px; text-align: left; }
        .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; }
        .card { background: #181818; padding: 15px; border-radius: 12px; width: 320px; border: 1px solid #333; text-align: left; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        video { width: 100%; border-radius: 8px; background: #000; margin-bottom: 10px; cursor: pointer; }
        .btn { background: #00e676; color: #000; display: block; padding: 10px; text-align: center; text-decoration: none; font-weight: bold; border-radius: 6px; margin-bottom: 8px; width: 100%; box-sizing: border-box; }
        .btn-dark { background: #2a2a2a; color: #fff; font-size: 13px; border: none;}
        .box { display: none; background: #111; padding: 10px; border-radius: 8px; margin-top: 8px; font-size: 12px; border: 1px solid #333; }
        .row { display: flex; align-items: center; background: #1a1a1a; margin-bottom: 6px; border-radius: 4px; border: 1px solid #333; }
        .txt { flex: 1; padding: 8px; color: #ddd; overflow-x: auto; white-space: nowrap; }
        .cpy { background: #4285f4; color: white; border: none; padding: 8px 12px; cursor: pointer; font-weight: bold; font-size: 11px; }
    </style></head>
    <body><h1>🇺🇸 USA 3D Animation Studio</h1><h2>🐍 Viral 3D Shorts</h2><div class='grid'>"""

    for h in history:
        vid = h['id']
        html += f"""<div class="card"><b>📅 {h['date']}</b>
            <video src="{h['file']}" controls preload="none"></video>
            <a href="{h['file']}" download class="btn">⬇️ Download</a>
            <button class="btn btn-dark" onclick="let b=document.getElementById('b-{vid}'); b.style.display = b.style.display==='block' ? 'none' : 'block'">📝 Details</button>
            <div class="box" id="b-{vid}">
                <div class="row"><div class="txt" id="t-{vid}">{h['title']}</div><button class="cpy" onclick="navigator.clipboard.writeText(document.getElementById('t-{vid}').innerText)">COPY</button></div>
                <div class="row"><div class="txt" id="d-{vid}">{h['desc']}</div><button class="cpy" onclick="navigator.clipboard.writeText(document.getElementById('d-{vid}').innerText)">COPY</button></div>
            </div></div>"""
    
    html += "</div></body></html>"
    with open("myrepo/index.html", "w") as f: f.write(html)
    
    os.chdir("myrepo")
    os.system('git config user.name "Kaggle GPU Bot"')
    os.system('git config user.email "bot@kaggle.com"')
    os.system('git add .')
    os.system('git commit -m "Auto Update: HQ 5B-I2V Video Ready 🚀"')
    os.system('git push origin main || git push origin master')
    print("✅ SUCCESS! Perfect 5B-I2V Video pushed to GitHub.")
