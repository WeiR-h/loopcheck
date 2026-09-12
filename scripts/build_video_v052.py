"""Assemble actual CUA screen captures; do not generate or modify app UI content."""
import json
from pathlib import Path
import subprocess
import imageio_ffmpeg

ROOT=Path(__file__).resolve().parents[1]
work=ROOT/'data/video-v052';work.mkdir(parents=True,exist_ok=True)
frames=ROOT/'.test-data/video-v052-frames'
ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
scenes=json.loads((ROOT/'docs/video/scenes-v052.json').read_text(encoding='utf-8'))
recordings={}
for scene in scenes:
    name=scene.get('capture')
    if not name:continue
    rows=json.loads((frames/(name+'.json')).read_text())
    lines=[]
    for n,row in enumerate(rows):
        filename=(frames/row['file']).as_posix().replace("'","'\\''")
        duration=(rows[n+1]['time']-row['time'])/1000 if n+1<len(rows) else .5
        lines.extend([f"file '{filename}'",f'duration {max(.02,duration):.4f}'])
    lines.append(lines[-2])
    listing=work/(name+'.txt');listing.write_text('\n'.join(lines),encoding='utf-8')
    output=work/(name+'.mp4')
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),
        '-vf','fps=24,pad=ceil(iw/2)*2:ceil(ih/2)*2','-c:v','libx264','-threads','2','-preset','veryfast','-crf','21','-pix_fmt','yuv420p',str(output)],check=True)
    scene['video']=output.relative_to(ROOT).as_posix()
    recordings[name]={'frames':len(rows),'first_capture_ms':rows[0]['time'],'last_capture_ms':rows[-1]['time'],
                      'disclosure':'Actual unaltered viewport frames; original frame intervals retained within this segment.'}

# Use the existing caption assembler, with this version's scene inputs and
# locally synthesized English audio. The underlying UI pixels remain original.
(work/'assembled-scenes.json').write_text(json.dumps(scenes,indent=2),encoding='utf-8')
source=(ROOT/'scripts/build_video_v05.py').read_text(encoding='utf-8')
source=source.replace("ROOT / 'data/video-v05'","ROOT / 'data/video-v052'")
source=source.replace("ROOT/'docs/video/scenes-v05.json'","ROOT/'data/video-v052/assembled-scenes.json'")
start=source.index('for i, scene in enumerate(scenes):')
end=source.index('\ntotal = 0',start)
source=source[:start]+"for i in range(len(scenes)):\n    assert (work/f'voice-{i}.wav').is_file(), 'Run scripts/narrate_v052.ps1 first'\n"+source[end:]
source=source.replace('LoopCheck-demo-en-v0.5.','LoopCheck-demo-en-v0.5.2.')
source=source.replace('v05-video-check.json','v052-video-check.json')
source=source.replace('Actual v0.5 recorded Chromium cart flows; silent audio track; English captions','Actual 0.5.2 CUA viewport sequences and UI screenshots; local synthetic English narration and captions')
source=source.replace('Edited evidence walkthrough, not a continuous desktop recording; real browser clips hold their last frame during explanation; faults deliberately injected','Edited evidence walkthrough with continuous captures within five stages and cuts between stages; final frames hold during explanation; cart requirements and edits are scripted presets; live planning evidence is separate')
exec(compile(source,str(ROOT/'scripts/build_video_v05.py'),'exec'),{'__file__':str(ROOT/'scripts/build_video_v05.py')})
(ROOT/'docs/evidence/v052-recording-segments.json').write_text(json.dumps(recordings,indent=2),encoding='utf-8')
