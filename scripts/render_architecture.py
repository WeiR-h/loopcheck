"""Render the implementation diagram for the contest's required architecture file."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import simpleSplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/pdf/LoopCheck-architecture.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
c = canvas.Canvas(str(OUT), pagesize=(1200, 780))
c.setTitle('LoopCheck 0.5.2 - Architecture')
c.setAuthor('LoopCheck')
INK, GREEN, MUTED = '#172e29', '#087f68', '#52675f'
c.setFillColor(HexColor('#f7f9f5')); c.rect(0,0,1200,780,fill=1,stroke=0)

def text(x,y,s,size=12,color=INK,bold=False):
    c.setFillColor(HexColor(color)); c.setFont('Helvetica-Bold' if bold else 'Helvetica',size); c.drawString(x,y,s)

def box(x,y,w,h,title,body,tint='#ffffff'):
    c.setFillColor(HexColor(tint)); c.setStrokeColor(HexColor('#cad8cf')); c.roundRect(x,y,w,h,10,fill=1,stroke=1)
    text(x+16,y+h-28,title,15,bold=True)
    yy=y+h-49
    for line in simpleSplit(body,'Helvetica',11.5,w-32):
        text(x+16,yy,line,11.5,MUTED); yy-=16
    assert yy >= y+7, title

def arrow(x1,y1,x2,y2,label=None):
    import math
    c.setStrokeColor(HexColor(GREEN)); c.setLineWidth(1.8); c.line(x1,y1,x2,y2)
    angle=math.atan2(y2-y1,x2-x1)
    for delta in (-.45,.45): c.line(x2,y2,x2-8*math.cos(angle+delta),y2-8*math.sin(angle+delta))
    if label: text((x1+x2)/2+5,(y1+y2)/2+6,label,10,GREEN)

text(42,730,'LoopCheck',33,bold=True)
text(260,736,'Keep approved behavior intact as AI changes your app',21,bold=True)
text(260,710,'Implementation architecture  |  Version 0.5.2  |  Strands Agents SDK',12,MUTED)
box(42,540,230,122,'1. Builder + web UI','Connect a trusted local preview. Describe future and preserved behavior. Review every requirement and browser check.')
box(342,540,248,122,'2. Strands planner','Observe live controls; explore bounded paths; propose requirements and trial-run checks. Never approve or weaken expectations.','#e9f6ef')
box(660,540,230,122,'3. Approved contract','SQLite: stable requirement IDs, revisions, enable state and optional executable flows. Uncovered items stay incomplete.')
box(945,540,215,122,'Provider + budget','Qwen3.7 Flash via Model Studio Beijing. Server-side key. Persistent reservations before each model request.')
arrow(272,606,342,606); arrow(590,606,660,606)
c.setStrokeColor(HexColor(GREEN)); c.setLineWidth(1.8)
c.line(1052,662,1052,687); c.line(1052,687,466,687); arrow(466,687,466,662)
box(42,333,230,128,'Existing coding AI','Edits the original project. Local stdio MCP: prepare_change, check_change, get_result. MCP cannot confirm drafts.')
box(342,333,248,128,'4. Source + watcher','Hash included frontend files. Debounce saves. Bind each run to its source and requirement versions. Ignore secrets and build outputs.')
box(660,333,230,128,'5. Browser verifier','Serialized Chromium subprocess. Fresh context per flow. Same-origin requests only. No model call for ordinary rechecks.','#e9f6ef')
box(945,333,215,128,'6. Evidence + verdict','Assertions, screenshots, complete reproduction and related files. Passed, failed, incomplete or inconclusive.')
arrow(157,540,157,461); arrow(272,397,342,397); arrow(590,397,660,397); arrow(775,540,775,461); arrow(890,397,945,397)
arrow(1050,333,1050,281); arrow(1050,281,157,281); arrow(157,281,157,333)
text(435,291,'Evidence returns to the coding tool; the same requirements are checked again.',12,GREEN)
box(42,100,550,130,'Acceptance is a versioned decision','can_accept = active scope exists + every requirement has a confirmed flow + every flow passes + current source and contract match + this is the latest check. Interrupted, stale, empty or uncovered scopes never pass.','#edf4ee')
box(622,100,538,130,'Local edition and public evaluation','Local: trusted project directory + running loopback preview + MCP. Public: bundled samples only, isolated sessions and persistent state. Keyless walkthrough uses disclosed presets; live planning uses the configured provider. AgentCore is not deployed.')
text(42,57,'MIT source: github.com/WeiR-h/loopcheck',12,GREEN)
text(42,36,'Scope: small frontend apps. Not a backend, login/payment or hostile-repository verification service.',11,MUTED)
c.save()
print(OUT)
