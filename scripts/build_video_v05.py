"""Assemble actual browser recordings and UI screenshots with English captions."""
from pathlib import Path
import json, re, subprocess, textwrap, wave
import imageio_ffmpeg

ROOT = Path(__file__).resolve().parents[1]
work = ROOT / 'data/video-v05'
dist = ROOT / 'dist'
dist.mkdir(exist_ok=True)
ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
scenes = json.loads((ROOT/'docs/video/scenes-v05.json').read_text(encoding='utf-8'))
work.mkdir(parents=True, exist_ok=True)
# Silent track and captions are the reproducible default; no speech service is required.
for i, scene in enumerate(scenes):
    duration = len(scene['narration'].split()) / 2.8
    with wave.open(str(work/f'voice-{i}.wav'), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b'\x00\x00' * int(duration * 16000))

total = 0
all_srt = []
def stamp(t, ass=False):
    h=int(t//3600); m=int(t//60)%60; s=t%60
    return f'{h}:{m:02}:{s:05.2f}' if ass else f'{h:02}:{m:02}:{int(s):02},{int(s%1*1000):03}'

for i, scene in enumerate(scenes):
    with wave.open(str(work/f'voice-{i}.wav')) as wav:
        duration=wav.getnframes()/wav.getframerate()+1
    lines=['[Script Info]', 'ScriptType: v4.00+', 'PlayResX: 1920', 'PlayResY: 1080',
      '[V4+ Styles]',
      'Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding',
      'Style: Default,Arial,32,&H00FFFFFF,&H00FFFFFF,&H00122319,&H00122319,0,0,0,0,100,100,0,0,3,1,0,2,110,110,18,1',
      'Style: Title,Arial,29,&H00FFFFFF,&H00FFFFFF,&H00122319,&H00122319,-1,0,0,0,100,100,0,0,3,1,0,8,100,100,12,1',
      '[Events]','Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text',
      f'Dialogue: 0,0:00:00.00,{stamp(duration,True)},Title,,0,0,0,,{scene["title"]}']
    sentences = re.split(r'(?<=[.!?])\s+',scene['narration'])
    cursor=0; words=sum(len(s.split()) for s in sentences)
    for sentence in sentences:
        end=cursor+(duration-1)*len(sentence.split())/words
        caption='\\N'.join(textwrap.wrap(sentence,width=108))
        lines.append(f'Dialogue: 0,{stamp(cursor,True)},{stamp(end,True)},Default,,0,0,0,,{caption}')
        all_srt.append(f'{len(all_srt)+1}\n{stamp(total+cursor)} --> {stamp(total+end)}\n{sentence}\n')
        cursor=end
    (work/f'scene-{i}.ass').write_text('\n'.join(lines),encoding='utf-8')
    command=[ffmpeg,'-hide_banner','-loglevel','error','-y',*(['-i',str(ROOT/scene['video'])] if scene.get('video') else ['-loop','1','-framerate','12','-i',str(ROOT/scene['image'])]),'-i',str(work/f'voice-{i}.wav'),
        '-vf',f'fps=24,tpad=stop_mode=clone:stop_duration=60,scale=1920:900:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:60:color=0x122319,subtitles=scene-{i}.ass',
        '-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',
        '-c:a','aac','-b:a','128k','-af','apad','-t',str(duration),str(work/f'clip-{i}.mp4')]
    subprocess.run(command,cwd=work,check=True)
    total += duration
    print(f'Encoded scene {i+1}/{len(scenes)}',flush=True)
(work/'concat.txt').write_text('\n'.join(f"file 'clip-{i}.mp4'" for i in range(len(scenes))),encoding='utf-8')
output=dist/'LoopCheck-demo-en-v0.5.mp4'
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i','concat.txt',
    '-c','copy','-movflags','+faststart',str(output)],cwd=work,check=True)
(dist/'LoopCheck-demo-en-v0.5.srt').write_text('\n'.join(all_srt),encoding='utf-8')
assert total < 300, total
subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(output),'-f','null','-'],check=True)
metadata={'duration_seconds':round(total,2),'format':'1920x1080 H.264/AAC','source':'Actual v0.5 recorded Chromium cart flows; silent audio track; English captions','disclosure':'Edited evidence walkthrough, not a continuous desktop recording; real browser clips hold their last frame during explanation; faults deliberately injected','bytes':output.stat().st_size}
(ROOT/'docs/evidence/v05-video-check.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
print(json.dumps(metadata))
