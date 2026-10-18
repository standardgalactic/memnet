"""Write the self-contained HTML page for a scene: view.js, the scene and drawing code in one file."""

from pathlib import Path

from .scene import to_json

VIEW_JS = Path(__file__).with_name("view.js").read_text(encoding="utf-8")

TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Corrective Navigation Viewer</title>
<style>
:root{--bg:#f6f5f1;--fg:#1d1d1b;--mut:#6b6a63;--panel:#fffefb;--line:#cfccc2;--sup:#1f7a6d;--con:#b7791f;--def:#b3392f;--una:#7a7a74;--rev:#6b3fa0}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#17171a;--fg:#ecebe6;--mut:#a09f97;--panel:#202024;--line:#44444a;--sup:#4cc2b0;--con:#e0a53c;--def:#ef7a6f;--una:#9a9a94;--rev:#b68ae6}}
:root[data-theme=dark]{--bg:#17171a;--fg:#ecebe6;--mut:#a09f97;--panel:#202024;--line:#44444a;--sup:#4cc2b0;--con:#e0a53c;--def:#ef7a6f;--una:#9a9a94;--rev:#b68ae6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;display:flex;flex-direction:column;height:100vh}
header{padding:10px 16px;border-bottom:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center}
h1{font-size:16px;margin:0;font-weight:600}
.legend{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;color:var(--mut)}
main{flex:1;display:flex;min-height:0;flex-wrap:wrap}
#stage{flex:2 1 420px;min-height:300px;position:relative}
canvas{width:100%;height:100%;display:block;touch-action:none}
aside{flex:1 1 300px;max-width:100%;border-left:1px solid var(--line);background:var(--panel);padding:12px 16px;overflow:auto}
pre{white-space:pre-wrap;word-break:break-word;font:12.5px/1.5 ui-monospace,monospace;margin:0}
button{font:inherit;padding:3px 10px;border:1px solid var(--line);background:var(--panel);color:var(--fg);border-radius:6px;cursor:pointer}
.hint{color:var(--mut);font-size:12px}
</style></head><body>
<header><h1>Corrective Navigation</h1>
<button id="prov" aria-pressed="false">Show provisional</button>
<button id="clear">Clear path</button>
<div class="legend">
<span>Distance: relevance</span><span>+ supported</span><span>&plusmn; contested</span><span>&times; defeated</span><span>&middot; unassessed</span>
<span>Arch above a node: door (solid open, faint dimmed)</span>
<span>Thin line: relevance &middot; Arrow: support &middot; Chevron: admissibility</span>
<span>Dashed: provisional &middot; Dotted: unverified &middot; Purple ring: needs review</span>
</div></header>
<main><div id="stage"><canvas id="c" aria-label="Spatial view of the claim graph"></canvas></div>
<aside><div class="hint">Drag to rotate, wheel to zoom, click a node or a line to see the events behind it. Your path stays in this page and is not written to the ledger.</div>
<pre id="out"></pre></aside></main>
<script>__VIEW_JS__</script>
<script>
var SCENE = __SCENE__;
var cam = {yaw: 0.6, pitch: 0.35, zoom: 1}, showProv = false, trail = [], items = [];
var cv = document.getElementById("c"), ctx = cv.getContext("2d"), out = document.getElementById("out");
function css(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim();}
function size(){var r=cv.getBoundingClientRect(),d=window.devicePixelRatio||1;cv.width=r.width*d;cv.height=r.height*d;ctx.setTransform(d,0,0,d,0,0);}
function toScreen(x,y){var r=cv.getBoundingClientRect(),s=Math.min(r.width,r.height)*0.42;return [r.width/2+x*s,r.height/2-y*s];}
function fromScreen(px,py){var r=cv.getBoundingClientRect(),s=Math.min(r.width,r.height)*0.42;return [(px-r.width/2)/s,-(py-r.height/2)/s];}
function dash(d){return d==="dashed"?[7,5]:d==="dotted"?[2,4]:[];}
function draw(){
  items = CNView.buildDisplayList(SCENE, {camera: cam, showProvisional: showProv, trail: trail});
  window.__items = items;
  var r=cv.getBoundingClientRect(); ctx.clearRect(0,0,r.width,r.height);
  items.filter(function(i){return i.kind==="trail";}).forEach(function(t){
    var a=toScreen(t.x1,t.y1),b=toScreen(t.x2,t.y2);ctx.strokeStyle=css("--rev");ctx.globalAlpha=.35;ctx.lineWidth=5;ctx.setLineDash([]);
    ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.globalAlpha=1;});
  items.filter(function(i){return i.kind==="edge";}).forEach(function(e){
    var a=toScreen(e.x1,e.y1),b=toScreen(e.x2,e.y2);
    ctx.setLineDash(dash(e.dash));ctx.strokeStyle=css("--fg");ctx.fillStyle=css("--fg");
    ctx.lineWidth=e.shape==="thin-line"?0.8:1.6;ctx.globalAlpha=e.shape==="thin-line"?.5:.6;
    ctx.beginPath();ctx.moveTo(a[0],a[1]);ctx.lineTo(b[0],b[1]);ctx.stroke();ctx.setLineDash([]);
    if(e.shape!=="thin-line"){var ang=Math.atan2(b[1]-a[1],b[0]-a[0]),mx=(a[0]+b[0])/2,my=(a[1]+b[1])/2,k=e.shape==="arrow"?8:6;
      ctx.beginPath();ctx.moveTo(mx,my);ctx.lineTo(mx-k*Math.cos(ang-0.5),my-k*Math.sin(ang-0.5));
      if(e.shape==="arrow"){ctx.lineTo(mx-k*Math.cos(ang+0.5),my-k*Math.sin(ang+0.5));ctx.closePath();ctx.fill();}else{ctx.moveTo(mx,my);ctx.lineTo(mx-k*Math.cos(ang+0.5),my-k*Math.sin(ang+0.5));ctx.stroke();}}
    ctx.globalAlpha=1;});
  var placed=[];
  items.filter(function(i){return i.kind==="node";}).sort(function(a,b){return b.depth-a.depth;}).forEach(function(n){
    var p=toScreen(n.x,n.y),rad=7*n.scale+3,col=css(n.support==="supported"?"--sup":n.support==="contested"?"--con":n.support==="defeated"?"--def":"--una");
    ctx.setLineDash(n.glyph==="dotted-ring"?[2,3]:[]);ctx.lineWidth=2;ctx.strokeStyle=col;ctx.fillStyle=col;
    ctx.beginPath();ctx.arc(p[0],p[1],rad,0,6.2832);
    if(n.glyph==="disc"){ctx.fill();}else if(n.glyph==="cross"){ctx.stroke();}else{ctx.stroke();}
    ctx.setLineDash([]);
    if(n.review){ctx.strokeStyle=css("--rev");ctx.lineWidth=2;ctx.beginPath();ctx.arc(p[0],p[1],rad+4,0,6.2832);ctx.stroke();}
    ctx.fillStyle=css("--bg");ctx.font="bold "+Math.round(rad*1.3)+"px system-ui";ctx.textAlign="center";ctx.textBaseline="middle";
    if(n.glyph==="disc")ctx.fillText(n.mark,p[0],p[1]+0.5);else{ctx.fillStyle=col;ctx.fillText(n.mark,p[0],p[1]+0.5);}
    if(n.doorGlyph){ctx.globalAlpha=n.doorGlyph==="arch-open"?1:.35;ctx.strokeStyle=css("--fg");ctx.lineWidth=1.6;
      ctx.beginPath();ctx.moveTo(p[0]-5,p[1]-rad-2);ctx.lineTo(p[0]-5,p[1]-rad-9);ctx.arc(p[0],p[1]-rad-9,5,Math.PI,0);ctx.lineTo(p[0]+5,p[1]-rad-2);ctx.stroke();ctx.globalAlpha=1;}
  });
  items.filter(function(i){return i.kind==="node";}).sort(function(a,b){return a.depth-b.depth;}).forEach(function(n){
    var p=toScreen(n.x,n.y),rad=7*n.scale+3;ctx.fillStyle=css("--fg");ctx.font="11px system-ui";ctx.textAlign="center";ctx.textBaseline="top";
    var ly=p[1]+rad+3,clash=placed.some(function(q){return Math.abs(q[0]-p[0])<70&&Math.abs(q[1]-ly)<12;});
    if(!clash||trail.indexOf(n.id)>=0){ctx.fillText(n.id,p[0],ly);placed.push([p[0],ly]);}});
}
function show(it){
  var key=it.key,txt=CNView.inspect(SCENE,key);
  if(it.kind==="node"){var mv=CNView.movement(SCENE,it.id);if(mv)txt+="\n\n"+mv;
    var rv=SCENE.nodes.filter(function(n){return n.id===it.id;})[0].review;if(rv.length)txt="Review: "+rv.join(", ")+"\n\n"+txt;}
  out.textContent=txt;window.__panel=txt;
}
cv.addEventListener("click",function(ev){var r=cv.getBoundingClientRect(),q=fromScreen(ev.clientX-r.left,ev.clientY-r.top),s=Math.min(r.width,r.height)*0.42;
  var it=CNView.pick(items,q[0],q[1],16/s,8/s);if(!it)return;
  if(it.kind==="node"&&trail[trail.length-1]!==it.id)trail.push(it.id);show(it);draw();});
var drag=null;
cv.addEventListener("pointerdown",function(e){drag=[e.clientX,e.clientY,cam.yaw,cam.pitch,false];cv.setPointerCapture(e.pointerId);});
cv.addEventListener("pointermove",function(e){if(!drag)return;var dx=e.clientX-drag[0],dy=e.clientY-drag[1];if(Math.abs(dx)+Math.abs(dy)>3)drag[4]=true;
  cam.yaw=drag[2]+dx*0.008;cam.pitch=Math.max(-1.4,Math.min(1.4,drag[3]+dy*0.008));draw();});
cv.addEventListener("pointerup",function(){drag=null;});
cv.addEventListener("wheel",function(e){e.preventDefault();cam.zoom=Math.max(0.3,Math.min(4,cam.zoom*(e.deltaY<0?1.1:0.9)));draw();},{passive:false});
document.getElementById("prov").onclick=function(){showProv=!showProv;this.setAttribute("aria-pressed",showProv);this.textContent=showProv?"Hide provisional":"Show provisional";draw();};
document.getElementById("clear").onclick=function(){trail=[];draw();};
window.addEventListener("resize",function(){size();draw();});
window.__screen=function(key){var it=items.filter(function(i){return i.key===key;})[0];if(!it)return null;
  var p=toScreen(it.x,it.y),r=cv.getBoundingClientRect();return [r.left+p[0],r.top+p[1]];};
window.__show=function(key){var it=items.filter(function(i){return i.key===key;})[0];if(it)show(it);};
size();draw();
</script></body></html>
"""


def render_html(scene):
    return (TEMPLATE.replace("__VIEW_JS__", VIEW_JS)
            .replace("__SCENE__", to_json(scene).replace("</", "<\\/")))


def write_page(scene, path):
    Path(path).write_text(render_html(scene), encoding="utf-8")


def main(argv=None):
    import argparse
    from ...ledger import Ledger
    from .scene import build_scene
    ap = argparse.ArgumentParser(description="Write the spatial viewer page for a ledger")
    ap.add_argument("ledger")
    ap.add_argument("out")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--version", type=int, default=None)
    ap.add_argument("--since", type=int, default=None, help="earlier version to explain movement against")
    ap.add_argument("--ledger-arm", action="store_true", help="include repair review status (L)")
    args = ap.parse_args(argv)
    scene = build_scene(Ledger(args.ledger), args.seed, version=args.version, L=args.ledger_arm,
                        since=args.since)
    write_page(scene, args.out)
    print(f"wrote {args.out}: {len(scene['nodes'])} nodes, {len(scene['edges'])} relations")


if __name__ == "__main__":
    main()
