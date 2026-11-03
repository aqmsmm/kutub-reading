#!/usr/bin/env python3
"""Generate section audio for books in data/books.js.
Usage: python3 tools/make_audio.py [--force] [--edge]
Uses ElevenLabs (Chaouki voice, eleven_v3); falls back to edge-tts ar-SA-HamedNeural.
Output compressed to mono 32k mp3 under audio/. Skips existing files unless --force."""
import json,os,re,sys,subprocess,tempfile,requests
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE="G1HOkzin3NMwRHSq60UI"; EDGE="/home/box/.local/bin/edge-tts"
FORCE="--force" in sys.argv; USE_EDGE="--edge" in sys.argv; used=set()
ORD=["الأول","الثاني","الثالث","الرابع","الخامس","السادس","السابع","الثامن","التاسع","العاشر","الحادي عشر","الثاني عشر"]
def spoken(t):
    t=re.sub(r'ص (\d+)–(\d+)',r'من صفحة \1 إلى صفحة \2',t); t=re.sub(r'ص (\d+)',r'صفحة \1',t)
    return t.replace('(','، ').replace(')','، ').replace('«','').replace('»','').replace('John Hull','')
def tts(text,raw):
    global USE_EDGE
    if not USE_EDGE:
        try:
            r=requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE}?output_format=mp3_44100_128",
              headers={"xi-api-key":os.environ["ELEVENLABS_API_KEY"]},
              json={"text":text,"model_id":"eleven_v3","language_code":"ar","voice_settings":{"stability":0.5,"similarity_boost":0.8,"style":0.1,"use_speaker_boost":True}},timeout=300)
            r.raise_for_status(); open(raw,"wb").write(r.content); used.add("elevenlabs"); return
        except Exception as e:
            print("ElevenLabs failed, using edge-tts:",e,getattr(e,'response',None) and e.response.text[:300]); USE_EDGE=True
    subprocess.run([EDGE,"--voice","ar-SA-HamedNeural","--text",text,"--write-media",raw],check=True); used.add("edge-tts")
def make(path,parts):
    """parts: a string or a list of strings (each generated separately, then joined; avoids truncation)."""
    out=os.path.join(ROOT,path)
    if os.path.exists(out) and not FORCE: return
    if isinstance(parts,str): parts=[parts]
    d=tempfile.mkdtemp(); lst=[]
    for i,t in enumerate(parts):
        raw=f"{d}/{i}.mp3"; tts(spoken(t),raw); lst.append(f"file '{raw}'")
    open(f"{d}/l.txt","w").write("\n".join(lst))
    subprocess.run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",f"{d}/l.txt","-ac","1","-b:a","32k",out],check=True); print("wrote",path)
s=open(os.path.join(ROOT,"data/books.js")).read(); B=json.loads(s[s.index("["):s.rindex("]")+1])
for b in B:
    name=f"كتاب {b['title']}، لـ{b['author']}"
    for c in b.get("chapters",[]): make(c["audio"],f"{c['title']}. {c['text']}")
    if b.get("summariesAudio"): make(b["summariesAudio"],f"ملخص فصول {name}. "+" ".join(f"{c['title']}. {c['text']}" for c in b["chapters"]))
    if b.get("lessonsAudio"): make(b["lessonsAudio"],[f"أهم الدروس والعبر من {name}."]+[f"الدرس {ORD[i]}: {l}" for i,l in enumerate(b["lessons"])])
    if b.get("quotesAudio"): make(b["quotesAudio"],f"اقتباسات من {name}. "+" ".join(f"من صفحة {q['page']}: {q['text']}" for q in b["quotes"]))
print("TTS used:",used or "none (all existed)")
