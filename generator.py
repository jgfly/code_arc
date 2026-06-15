"""
HTML visualization generator.

Generates a self-contained interactive HTML file with:
- Module/Class/Function blocks with distinct colors, arranged in a loose 2D layout
- Function-granularity call edges with arrows at exact block edges
- Hover-to-highlight + click-to-lock edge highlighting with z-index management
- Click-to-view source code, Zoom/pan, Search, Filter
"""

import html
import json

from .analyzer import ClassInfo, FuncInfo, ModuleInfo, ProjectData


class HTMLGenerator:
    def __init__(self, project_data: ProjectData, title: str = "Code Arc"):
        self.data = project_data
        self.title = title

    def generate(self) -> str:
        nodes_json = self._generate_nodes_json()
        edges_json = self._generate_edges_json()
        inheritance_json = self._generate_inheritance_json()
        source_json = self._generate_source_json()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html.escape(self.title)} - Code Arc</title>
<style>
{self._get_css()}
</style>
</head>
<body>
{self._get_html_body(nodes_json, edges_json, inheritance_json, source_json)}
<script>
{self._get_javascript()}
</script>
</html>
</html>"""

    def _generate_nodes_json(self) -> str:
        nodes = []
        for module in self.data.modules:
            module_node = {"id": module.name, "type": "module", "name": module.name,
                "label": module.name.split(".")[-1] or module.name,
                "full_name": module.name, "file_path": module.file_path, "children": []}
            for cls in module.classes:
                class_node = {"id": cls.full_name, "type": "class", "name": cls.name,
                    "full_name": cls.full_name, "init_params": cls.init_params,
                    "bases": cls.bases, "lineno": cls.lineno, "children": []}
                for method in cls.methods:
                    class_node["children"].append({"id": method.full_name, "type": "method",
                        "name": method.name, "full_name": method.full_name,
                        "params": method.params, "return_type": method.return_type,
                        "lineno": method.lineno})
                module_node["children"].append(class_node)
            for func in module.functions:
                module_node["children"].append({"id": func.full_name, "type": "function",
                    "name": func.name, "full_name": func.full_name,
                    "params": func.params, "return_type": func.return_type,
                    "lineno": func.lineno})
            nodes.append(module_node)
        return json.dumps(nodes, ensure_ascii=False)

    def _generate_edges_json(self) -> str:
        return json.dumps([{"source": s, "target": t, "type": "call"}
                           for s, t in self.data.call_edges], ensure_ascii=False)

    def _generate_inheritance_json(self) -> str:
        return json.dumps([{"source": s, "target": t, "type": "inherit"}
                           for s, t in self.data.class_inheritance], ensure_ascii=False)

    def _generate_source_json(self) -> str:
        sources = {}
        for m in self.data.modules:
            for c in m.classes:
                sources[c.full_name] = c.source_code
                for mt in c.methods:
                    sources[mt.full_name] = mt.source_code
            for f in m.functions:
                sources[f.full_name] = f.source_code
        return json.dumps(sources, ensure_ascii=False)

    def _get_css(self) -> str:
        return """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI','Inter',-apple-system,BlinkMacSystemFont,sans-serif;
  background:#0d0e1a;color:#e0e0e0;overflow:hidden;height:100vh;width:100vw}

#toolbar{position:fixed;top:0;left:0;right:0;height:50px;
  background:linear-gradient(180deg,#14152a,#10112a);border-bottom:1px solid #222340;
  display:flex;align-items:center;padding:0 20px;z-index:100;gap:10px}
#toolbar .logo{font-size:16px;font-weight:800;
  background:linear-gradient(135deg,#64b5f6,#9c7cff);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:1px}
#toolbar .project-name{font-size:13px;color:#555570;
  border-left:1px solid #2a2b45;padding-left:12px;margin-left:4px}
#search-box{margin-left:auto;padding:7px 14px 7px 36px;border-radius:8px;
  border:1px solid #222340;
  background:#181930 url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' fill='%23666' viewBox='0 0 16 16'%3E%3Cpath d='M11.742 10.344a6.5 6.5 0 1 0-1.397 1.398h-.001l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85zm-5.242.656a5 5 0 1 1 0-10 5 5 0 0 1 0 10z'/%3E%3C/svg%3E") 12px center no-repeat;
  color:#e0e0e0;font-size:13px;width:240px;outline:none;transition:border-color .2s,width .3s}
#search-box:focus{border-color:#64b5f680;width:300px}
#search-box::placeholder{color:#444460}
.toolbar-btn{padding:5px 13px;border-radius:7px;border:1px solid #222340;
  background:#181930;color:#8888aa;font-size:12px;cursor:pointer;
  transition:all .2s;white-space:nowrap}
.toolbar-btn:hover{background:#222250;border-color:#444470;color:#bbb}
.toolbar-btn.active{background:#1a2a4a;border-color:#4488bb;color:#66aaee}
.toolbar-sep{width:1px;height:24px;background:#222340}

#canvas-container{position:fixed;top:50px;left:0;right:0;bottom:0;
  overflow:hidden;cursor:grab;
  background:radial-gradient(circle at 20% 30%,rgba(40,50,80,.15) 0%,transparent 50%),
    radial-gradient(circle at 80% 70%,rgba(60,30,70,.1) 0%,transparent 50%),#0d0e1a}
#canvas-container.grabbing{cursor:grabbing}
#canvas{position:absolute;transform-origin:0 0}

/* SVG layer */
#edge-svg{position:absolute;top:0;left:0;pointer-events:none;overflow:visible;z-index:1}
#edge-svg path.e{pointer-events:stroke;cursor:pointer}
#edge-svg.on-top{z-index:50}

/* Blocks above SVG by default, but below when edges are on-top */
.module-block,.class-block,.func-block,.method-block{position:relative;z-index:2}

/* When edges on-top, push blocks below */
body.edges-on-top .module-block,
body.edges-on-top .class-block,
body.edges-on-top .func-block,
body.edges-on-top .method-block{z-index:1}
body.edges-on-top #edge-svg{z-index:50}

.module-block{position:absolute;
  background:linear-gradient(160deg,#181930,#151628);
  border:1.5px solid #2a2b5540;border-radius:14px;min-width:180px;
  box-shadow:0 8px 32px rgba(0,0,0,.35);transition:box-shadow .3s}
.module-block:hover{box-shadow:0 8px 40px rgba(40,40,90,.35),0 0 0 1px rgba(60,60,120,.2)}
.module-header{background:linear-gradient(135deg,#3e4280,#33366a);
  padding:10px 16px;border-radius:12px 12px 0 0;font-size:13px;font-weight:700;
  color:#c8c8f0;letter-spacing:.4px;user-select:none;display:flex;align-items:center;gap:8px}
.module-header .mi{width:20px;height:20px;border-radius:4px;background:rgba(255,255,255,.12);
  display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0}
.module-body{padding:8px 8px 10px}

.class-block{background:linear-gradient(160deg,#162030,#142535);
  border:1px solid #1e557540;border-radius:10px;margin:7px 0;overflow:hidden;
  transition:border-color .2s,box-shadow .2s}
.class-block:hover{border-color:#2a8aaa;box-shadow:0 4px 16px rgba(30,85,117,.15)}
.class-header{background:linear-gradient(135deg,#1e6a8a,#1a5a78);
  padding:7px 13px;font-size:12.5px;font-weight:600;color:#a0d8f0;cursor:pointer;
  display:flex;align-items:center;gap:6px;transition:background .2s}
.class-header:hover{background:linear-gradient(135deg,#2878a0,#226a8a)}
.class-header .ci{width:17px;height:17px;border-radius:3px;background:rgba(255,255,255,.12);
  display:flex;align-items:center;justify-content:center;font-size:10px;flex-shrink:0}
.class-bases{font-size:11px;color:#5a98b8;font-weight:400}
.class-params{padding:4px 13px 6px;font-size:10.5px;color:#5a90aa;
  font-family:'Cascadia Code','Fira Code','Consolas',monospace;line-height:1.5;
  border-bottom:1px solid #1e557525;word-break:break-all}
.class-params .pl{color:#3a7a9a;font-weight:600}
.class-body{padding:4px 5px 6px}

.func-block{background:linear-gradient(160deg,#142014,#122518);
  border:1px solid #2a6a2a40;border-radius:7px;margin:4px 2px;cursor:pointer;
  transition:border-color .2s,box-shadow .2s,transform .15s}
.func-block:hover{border-color:#3a9a3a;box-shadow:0 2px 10px rgba(42,106,42,.15);transform:translateY(-1px)}
.func-header{padding:5px 11px;font-size:12px;font-weight:600;color:#80d880;
  display:flex;align-items:center;gap:5px}
.func-header .fi{width:15px;height:15px;border-radius:3px;background:rgba(60,160,60,.12);
  display:flex;align-items:center;justify-content:center;font-size:9px;color:#50a050;
  flex-shrink:0;font-weight:700}
.func-signature{padding:1px 11px 5px 31px;font-size:10px;color:#508a50;
  font-family:'Cascadia Code','Fira Code','Consolas',monospace;line-height:1.4;word-break:break-all}

.method-block{background:linear-gradient(160deg,#1e1420,#201828);
  border:1px solid #6a2a6a40;border-radius:7px;margin:3px 2px;cursor:pointer;
  transition:border-color .2s,box-shadow .2s,transform .15s}
.method-block:hover{border-color:#9a3a9a;box-shadow:0 2px 10px rgba(106,42,106,.15);transform:translateY(-1px)}
.method-header{padding:4px 11px;font-size:12px;font-weight:600;color:#c888c8;
  display:flex;align-items:center;gap:5px}
.method-header .fi{width:15px;height:15px;border-radius:3px;background:rgba(150,60,150,.12);
  display:flex;align-items:center;justify-content:center;font-size:9px;color:#a050a0;
  flex-shrink:0;font-weight:700}
.method-signature{padding:1px 11px 4px 31px;font-size:10px;color:#7a507a;
  font-family:'Cascadia Code','Fira Code','Consolas',monospace;line-height:1.4;word-break:break-all}

/* Source panel */
#source-panel{position:fixed;top:50px;right:-540px;width:520px;bottom:0;
  background:#0e0f22;border-left:1px solid #222340;z-index:90;
  transition:right .35s cubic-bezier(.4,0,.2,1);display:flex;flex-direction:column;
  box-shadow:-8px 0 32px rgba(0,0,0,.5)}
#source-panel.open{right:0}
#sp-hdr{padding:12px 16px;background:#14152a;border-bottom:1px solid #222340;
  display:flex;align-items:center;justify-content:space-between;gap:12px}
#sp-title{font-size:12px;font-weight:600;color:#5599cc;
  font-family:'Cascadia Code','Fira Code','Consolas',monospace;word-break:break-all}
#sp-close{background:none;border:1px solid #222340;color:#666;font-size:13px;
  cursor:pointer;padding:3px 10px;border-radius:5px;transition:all .2s}
#sp-close:hover{background:#222340;color:#ddd}
#sp-code{flex:1;overflow:auto;padding:14px 16px;
  font-family:'Cascadia Code','Fira Code','Consolas',monospace;
  font-size:12px;line-height:1.7;white-space:pre;color:#a8a8c8;tab-size:4}

/* Highlights */
.module-block.search-hit{box-shadow:0 0 0 3px #ffd54f,0 8px 32px rgba(255,213,79,.2)!important}
.class-block.search-hit{border-color:#ffd54f!important;box-shadow:0 0 0 2px #ffd54f60!important}
.func-block.search-hit,.method-block.search-hit{border-color:#ffd54f!important;box-shadow:0 0 0 2px #ffd54f60!important}
.block-hl{box-shadow:0 0 0 2px rgba(100,181,246,.5),0 0 16px rgba(100,181,246,.15)!important}

/* Legend */
#legend{position:fixed;bottom:16px;left:16px;background:#12132af0;border:1px solid #222340;
  border-radius:10px;padding:12px 16px;z-index:100;font-size:11px;backdrop-filter:blur(8px)}
#legend h3{font-size:10px;margin-bottom:8px;color:#555570;font-weight:600;
  text-transform:uppercase;letter-spacing:1px}
.legend-row{display:flex;align-items:center;gap:8px;margin:4px 0;color:#8888aa}
.legend-swatch{width:14px;height:10px;border-radius:2px;flex-shrink:0}
.legend-line{width:24px;height:2px;flex-shrink:0;border-radius:1px}

#stats{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);
  background:#12132af0;border:1px solid #222340;border-radius:8px;padding:6px 18px;
  font-size:11px;color:#555570;z-index:100;display:flex;gap:16px;backdrop-filter:blur(8px)}
.sv{color:#5599cc;font-weight:600}
#zoom{position:fixed;top:60px;right:16px;font-size:11px;color:#444460;z-index:100;
  font-family:'Cascadia Code','Fira Code',monospace}
#tip{position:fixed;background:#1a1b30f0;border:1px solid #333360;border-radius:7px;
  padding:7px 12px;font-size:11px;color:#b0b0d0;pointer-events:none;z-index:200;
  max-width:380px;display:none;box-shadow:0 4px 16px rgba(0,0,0,.5);
  font-family:'Cascadia Code','Fira Code','Consolas',monospace;backdrop-filter:blur(8px)}

::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:#0e0f22}
::-webkit-scrollbar-thumb{background:#333360;border-radius:3px}
::-webkit-scrollbar-thumb:hover{background:#4a4a80}
"""

    def _get_html_body(self, nodes_json: str, edges_json: str,
                       inheritance_json: str, source_json: str) -> str:
        return f"""
<div id="toolbar">
    <span class="logo">Code Arc</span>
    <span class="project-name">{html.escape(self.title)}</span>
    <input type="text" id="search-box" placeholder="Search modules, classes, functions..." />
    <div class="toolbar-sep"></div>
    <button class="toolbar-btn" id="btn-fit" title="Fit to screen (F)">Fit</button>
    <button class="toolbar-btn active" id="btn-calls" title="Toggle call edges">Calls</button>
    <button class="toolbar-btn active" id="btn-inherit" title="Toggle inheritance edges">Inherit</button>
    <button class="toolbar-btn" id="btn-top" title="Edges on top layer">Edges Top</button>
    <button class="toolbar-btn" id="btn-collapse" title="Collapse all">Collapse</button>
</div>
<div id="canvas-container">
    <div id="canvas">
        <svg id="edge-svg" xmlns="http://www.w3.org/2000/svg"></svg>
    </div>
</div>
<div id="source-panel">
    <div id="sp-hdr"><span id="sp-title">Source</span><button id="sp-close">Close</button></div>
    <pre id="sp-code"></pre>
</div>
<div id="legend">
    <h3>Legend</h3>
    <div class="legend-row"><div class="legend-swatch" style="background:linear-gradient(135deg,#3e4280,#33366a)"></div>Module</div>
    <div class="legend-row"><div class="legend-swatch" style="background:linear-gradient(135deg,#1e6a8a,#1a5a78)"></div>Class</div>
    <div class="legend-row"><div class="legend-swatch" style="background:#142014;border:1px solid #2a6a2a"></div>Function</div>
    <div class="legend-row"><div class="legend-swatch" style="background:#1e1420;border:1px solid #6a2a6a"></div>Method</div>
    <div class="legend-row"><div class="legend-line" style="background:#5b9bd5"></div>Call</div>
    <div class="legend-row"><div class="legend-line" style="background:#ff6b6b;border-top:2px dashed #ff6b6b;height:0"></div>Inherit</div>
</div>
<div id="stats">
    <span>Modules: <span class="sv" id="s-mod">0</span></span>
    <span>Classes: <span class="sv" id="s-cls">0</span></span>
    <span>Functions: <span class="sv" id="s-fn">0</span></span>
    <span>Edges: <span class="sv" id="s-edge">0</span></span>
</div>
<div id="zoom">100%</div>
<div id="tip"></div>
<script id="d-nodes" type="application/json">{nodes_json}</script>
<script id="d-edges" type="application/json">{edges_json}</script>
<script id="d-inherit" type="application/json">{inheritance_json}</script>
<script id="d-source" type="application/json">{source_json}</script>
"""

    def _get_javascript(self) -> str:
        return r"""
(function(){
"use strict";

var ND=JSON.parse(document.getElementById('d-nodes').textContent);
var ED=JSON.parse(document.getElementById('d-edges').textContent);
var ID=JSON.parse(document.getElementById('d-inherit').textContent);
var SD=JSON.parse(document.getElementById('d-source').textContent);

var scale=1,panX=40,panY=40;
var dragging=false,dsx=0,dsy=0,psx=0,psy=0;
var showCalls=true,showInherit=true,allCollapsed=false,edgesOnTop=false;
var searchTerm="";
var lockedId=null;  // id of the block whose edges are "locked" (clicked)

var ctnr=document.getElementById('canvas-container');
var cvs=document.getElementById('canvas');
var svg=document.getElementById('edge-svg');
var tip=document.getElementById('tip');
var zoomEl=document.getElementById('zoom');
var EM={};

// Stats
var nCls=0,nFn=0;
ND.forEach(function(m){m.children.forEach(function(c){if(c.type==='class')nCls++;else nFn++;})});
document.getElementById('s-mod').textContent=ND.length;
document.getElementById('s-cls').textContent=nCls;
document.getElementById('s-fn').textContent=nFn;
document.getElementById('s-edge').textContent=ED.length+ID.length;

function esc(s){var d=document.createElement('div');d.textContent=s;return d.innerHTML;}

// ========== Build DOM ==========
function buildAll(){
    ND.forEach(function(m){
        var el=buildModule(m);
        cvs.appendChild(el);
        EM[m.id]=el;
    });
    requestAnimationFrame(function(){
        layoutModules();
        requestAnimationFrame(function(){drawEdges();fitToScreen();});
    });
}

function layoutModules(){
    var groups={},groupOrder=[];
    ND.forEach(function(m){
        var parts=m.name.split('.');
        var gk=parts.length<=1?'_scripts':parts[0];
        if(!groups[gk]){groups[gk]=[];groupOrder.push(gk);}
        groups[gk].push(m);
    });
    Object.keys(groups).forEach(function(k){
        groups[k].sort(function(a,b){
            var da=a.name.split('.').length,db=b.name.split('.').length;
            return da!==db?da-db:a.name.localeCompare(b.name);
        });
    });
    groupOrder.sort(function(a,b){if(a==='_scripts')return -1;if(b==='_scripts')return 1;return a.localeCompare(b);});

    var sizes={};
    ND.forEach(function(m){
        var el=EM[m.id];
        if(el){var r=el.getBoundingClientRect();sizes[m.id]={w:r.width,h:r.height};}
    });

    var GAP_X=50,GAP_Y=40,GROUP_GAP_X=100,MAX_COLS=5;
    var groupX=0;

    groupOrder.forEach(function(gk){
        var mods=groups[gk];
        var cols=Math.min(mods.length,MAX_COLS);
        var groupStartX=groupX;

        mods.forEach(function(mod,idx){
            var col=idx%cols,row=Math.floor(idx/cols);
            var s=sizes[mod.id]||{w:300,h:200};
            var x=groupStartX;
            for(var c=0;c<col;c++){var cm=mods[row*cols+c];if(cm){var cs=sizes[cm.id]||{w:300};x+=cs.w+GAP_X;}}
            var rowY=0;
            for(var r=0;r<row;r++){var rh=0;for(var rc=0;rc<cols;rc++){var rm=mods[r*cols+rc];if(rm){var rs=sizes[rm.id]||{h:200};rh=Math.max(rh,rs.h);}}rowY+=rh+GAP_Y;}
            var el=EM[mod.id];
            if(el){el.style.left=x+'px';el.style.top=rowY+'px';}
        });

        var groupW=0;
        for(var c2=0;c2<cols;c2++){var lm=mods[c2];if(lm){var ls=sizes[lm.id]||{w:300};groupW+=ls.w+GAP_X;}}
        groupX+=groupW+GROUP_GAP_X;
    });
}

function buildModule(mod){
    var el=document.createElement('div');el.className='module-block';el.dataset.id=mod.id;
    var hdr=document.createElement('div');hdr.className='module-header';
    hdr.innerHTML='<span class="mi">M</span>'+esc(mod.label);hdr.title=mod.full_name;
    el.appendChild(hdr);
    var body=document.createElement('div');body.className='module-body';
    mod.children.forEach(function(ch){body.appendChild(ch.type==='class'?buildClass(ch):buildFunc(ch));});
    el.appendChild(body);return el;
}
function buildClass(cls){
    var el=document.createElement('div');el.className='class-block';el.dataset.id=cls.id;
    var hdr=document.createElement('div');hdr.className='class-header';
    var h='<span class="ci">C</span>'+esc(cls.name);
    if(cls.bases&&cls.bases.length>0)h+=' <span class="class-bases">→ '+esc(cls.bases.join(', '))+'</span>';
    hdr.innerHTML=h;hdr.addEventListener('click',function(ev){ev.stopPropagation();openSource(cls);});
    el.appendChild(hdr);
    if(cls.init_params&&cls.init_params.length>0){
        var p=document.createElement('div');p.className='class-params';
        p.innerHTML='<span class="pl">init</span>('+cls.init_params.map(function(x){return esc(x);}).join(', ')+')';
        el.appendChild(p);
    }
    if(cls.children&&cls.children.length>0){
        var cb=document.createElement('div');cb.className='class-body';
        cls.children.forEach(function(m){cb.appendChild(buildMethod(m));});
        el.appendChild(cb);
    }
    return el;
}
function buildFunc(fn){
    var el=document.createElement('div');el.className='func-block';el.dataset.id=fn.id;
    var hdr=document.createElement('div');hdr.className='func-header';
    var h='<span class="fi">f</span>'+esc(fn.name);
    if(fn.return_type)h+=' <span style="color:#408040;font-size:11px">→ '+esc(fn.return_type)+'</span>';
    hdr.innerHTML=h;hdr.addEventListener('click',function(ev){ev.stopPropagation();openSource(fn);});
    el.appendChild(hdr);
    if(fn.params&&fn.params.length>0){var s=document.createElement('div');s.className='func-signature';s.textContent='('+fn.params.join(', ')+')';el.appendChild(s);}
    return el;
}
function buildMethod(m){
    var el=document.createElement('div');el.className='method-block';el.dataset.id=m.id;
    var hdr=document.createElement('div');hdr.className='method-header';
    var h='<span class="fi">f</span>'+esc(m.name);
    if(m.return_type)h+=' <span style="color:#704080;font-size:11px">→ '+esc(m.return_type)+'</span>';
    hdr.innerHTML=h;hdr.addEventListener('click',function(ev){ev.stopPropagation();openSource(m);});
    el.appendChild(hdr);
    if(m.params&&m.params.length>0){var s=document.createElement('div');s.className='method-signature';s.textContent='('+m.params.join(', ')+')';el.appendChild(s);}
    return el;
}

// ========== Source Panel ==========
function openSource(item){
    document.getElementById('sp-title').textContent=item.full_name||item.id;
    document.getElementById('sp-code').textContent=SD[item.full_name||item.id]||'(Source not available)';
    document.getElementById('source-panel').classList.add('open');
}
document.getElementById('sp-close').addEventListener('click',function(){document.getElementById('source-panel').classList.remove('open');});

// ========== Measure ==========
function measure(){
    var pos={},cr=cvs.getBoundingClientRect();
    var els=cvs.querySelectorAll('[data-id]');
    for(var i=0;i<els.length;i++){
        var el=els[i],id=el.dataset.id,r=el.getBoundingClientRect();
        pos[id]={x:(r.left-cr.left)/scale,y:(r.top-cr.top)/scale,
            w:r.width/scale,h:r.height/scale,
            cx:(r.left-cr.left+r.width/2)/scale,cy:(r.top-cr.top+r.height/2)/scale};
    }
    return pos;
}

// ========== Edge Drawing ==========
function drawEdges(){
    svg.innerHTML='';

    // Arrow markers
    var defs=document.createElementNS('http://www.w3.org/2000/svg','defs');

    // Call arrow - bigger, more visible
    var mk1=document.createElementNS('http://www.w3.org/2000/svg','marker');
    mk1.setAttribute('id','a-call');mk1.setAttribute('viewBox','0 0 12 8');
    mk1.setAttribute('refX','11');mk1.setAttribute('refY','4');
    mk1.setAttribute('markerWidth','10');mk1.setAttribute('markerHeight','7');
    mk1.setAttribute('orient','auto');
    var p1=document.createElementNS('http://www.w3.org/2000/svg','path');
    p1.setAttribute('d','M0,0 L12,4 L0,8 Z');p1.setAttribute('fill','#5b9bd5');
    mk1.appendChild(p1);defs.appendChild(mk1);

    // Call arrow - highlighted version
    var mk1h=document.createElementNS('http://www.w3.org/2000/svg','marker');
    mk1h.setAttribute('id','a-call-hl');mk1h.setAttribute('viewBox','0 0 12 8');
    mk1h.setAttribute('refX','11');mk1h.setAttribute('refY','4');
    mk1h.setAttribute('markerWidth','10');mk1h.setAttribute('markerHeight','7');
    mk1h.setAttribute('orient','auto');
    var p1h=document.createElementNS('http://www.w3.org/2000/svg','path');
    p1h.setAttribute('d','M0,0 L12,4 L0,8 Z');p1h.setAttribute('fill','#7db8f0');
    mk1h.appendChild(p1h);defs.appendChild(mk1h);

    // Inherit arrow - hollow
    var mk2=document.createElementNS('http://www.w3.org/2000/svg','marker');
    mk2.setAttribute('id','a-inh');mk2.setAttribute('viewBox','0 0 12 8');
    mk2.setAttribute('refX','11');mk2.setAttribute('refY','4');
    mk2.setAttribute('markerWidth','10');mk2.setAttribute('markerHeight','7');
    mk2.setAttribute('orient','auto');
    var p2=document.createElementNS('http://www.w3.org/2000/svg','path');
    p2.setAttribute('d','M0,0 L12,4 L0,8 Z');p2.setAttribute('fill','#0d0e1a');
    p2.setAttribute('stroke','#ff6b6b');p2.setAttribute('stroke-width','1.5');
    mk2.appendChild(p2);defs.appendChild(mk2);

    // Inherit arrow - highlighted
    var mk2h=document.createElementNS('http://www.w3.org/2000/svg','marker');
    mk2h.setAttribute('id','a-inh-hl');mk2h.setAttribute('viewBox','0 0 12 8');
    mk2h.setAttribute('refX','11');mk2h.setAttribute('refY','4');
    mk2h.setAttribute('markerWidth','10');mk2h.setAttribute('markerHeight','7');
    mk2h.setAttribute('orient','auto');
    var p2h=document.createElementNS('http://www.w3.org/2000/svg','path');
    p2h.setAttribute('d','M0,0 L12,4 L0,8 Z');p2h.setAttribute('fill','#1a0e1a');
    p2h.setAttribute('stroke','#ff9090');p2h.setAttribute('stroke-width','2');
    mk2h.appendChild(p2h);defs.appendChild(mk2h);

    svg.appendChild(defs);

    var pos=measure();
    if(showCalls)ED.forEach(function(e){drawEdge(e.source,e.target,'call',pos);});
    if(showInherit)ID.forEach(function(e){drawEdge(e.source,e.target,'inherit',pos);});

    var maxX=0,maxY=0;
    Object.keys(pos).forEach(function(id){var p=pos[id];maxX=Math.max(maxX,p.x+p.w+200);maxY=Math.max(maxY,p.y+p.h+200);});
    svg.setAttribute('width',maxX);svg.setAttribute('height',maxY);
}

// Compute the exact point where a line from center cx,cy to tx,ty
// intersects the boundary of rectangle {x,y,w,h}
function rectEdgePoint(rect,tx,ty){
    var cx=rect.cx,cy=rect.cy;
    var dx=tx-cx,dy=ty-cy;
    if(dx===0&&dy===0)return{x:cx,y:cy};

    // Check intersection with each of the 4 sides
    var candidates=[];

    // Top side (y = rect.y): t = (rect.y - cy) / dy
    if(dy!==0){var t=(rect.y-cy)/dy;if(t>0){var ix=cx+dx*t;if(ix>=rect.x&&ix<=rect.x+rect.w)candidates.push({x:ix,y:rect.y,t:t});}}
    // Bottom side (y = rect.y + rect.h)
    if(dy!==0){var t2=(rect.y+rect.h-cy)/dy;if(t2>0){var ix2=cx+dx*t2;if(ix2>=rect.x&&ix2<=rect.x+rect.w)candidates.push({x:ix2,y:rect.y+rect.h,t:t2});}}
    // Left side (x = rect.x)
    if(dx!==0){var t3=(rect.x-cx)/dx;if(t3>0){var iy=cy+dy*t3;if(iy>=rect.y&&iy<=rect.y+rect.h)candidates.push({x:rect.x,y:iy,t:t3});}}
    // Right side (x = rect.x + rect.w)
    if(dx!==0){var t4=(rect.x+rect.w-cx)/dx;if(t4>0){var iy2=cy+dy*t4;if(iy2>=rect.y&&iy2<=rect.y+rect.h)candidates.push({x:rect.x+rect.w,y:iy2,t:t4});}}

    if(candidates.length===0)return{x:cx,y:cy};
    // Pick the closest intersection (smallest t)
    candidates.sort(function(a,b){return a.t-b.t;});
    return candidates[0];
}

function findPos(id,pos){
    if(pos[id])return pos[id];
    // Walk up to find parent
    var parts=id.split('.');
    for(var i=parts.length-1;i>0;i--){
        var c=parts.slice(0,i).join('.');
        if(pos[c])return pos[c];
    }
    return null;
}

function drawEdge(sourceId,targetId,type,pos){
    var sPos=findPos(sourceId,pos);
    var tPos=findPos(targetId,pos);
    if(!sPos||!tPos)return;

    // Compute edge start/end on exact rectangle boundary
    // Source edge point: ray from sPos center towards tPos center
    var srcPt=rectEdgePoint(sPos,tPos.cx,tPos.cy);
    var tgtPt=rectEdgePoint(tPos,sPos.cx,sPos.cy);

    var x1=srcPt.x,y1=srcPt.y;
    var x2=tgtPt.x,y2=tgtPt.y;

    // Bezier control points
    var dx=x2-x1,dy=y2-y1;
    var dist=Math.sqrt(dx*dx+dy*dy);
    var cx1,cy1,cx2,cy2;

    if(Math.abs(dy)>Math.abs(dx)*0.4){
        cx1=x1;cy1=y1+dy*0.35;
        cx2=x2;cy2=y2-dy*0.35;
        var offset=(Math.sin(x1*0.01+y1*0.01)*0.5+0.5)*30-15;
        cx1+=offset;cx2+=offset;
    }else{
        cx1=x1+dx*0.35;cy1=y1;
        cx2=x1+dx*0.65;cy2=y2;
        var offy=(Math.sin(x1*0.01+y1*0.01)*0.5+0.5)*30-15;
        cy1+=offy;cy2+=offy;
    }

    var path=document.createElementNS('http://www.w3.org/2000/svg','path');
    path.setAttribute('d','M'+x1+','+y1+' C'+cx1+','+cy1+' '+cx2+','+cy2+' '+x2+','+y2);
    path.classList.add('e');

    var isCall=type==='call';
    path.setAttribute('stroke',isCall?'#5b9bd540':'#ff6b6b40');
    path.setAttribute('stroke-width','1.5');
    path.setAttribute('fill','none');
    path.setAttribute('marker-end',isCall?'url(#a-call)':'url(#a-inh)');
    if(!isCall)path.setAttribute('stroke-dasharray','8,5');

    path.dataset.source=sourceId;
    path.dataset.target=targetId;
    path.dataset.edgeType=type;

    // Edge hover
    path.addEventListener('mouseenter',function(ev){
        highlightEdge(this,true);
        var sn=sourceId.split('.').slice(-2).join('.');
        var tn=targetId.split('.').slice(-2).join('.');
        showTip(ev,sn+' → '+tn);
        hlBlocks(sourceId,targetId);
    });
    path.addEventListener('mousemove',function(ev){
        tip.style.left=(ev.clientX+14)+'px';tip.style.top=(ev.clientY+14)+'px';
    });
    path.addEventListener('mouseleave',function(){
        if(!isLockedConnected(this))highlightEdge(this,false);
        hideTip();clearBlockHL();
    });

    svg.appendChild(path);
}

function highlightEdge(el,on){
    var isCall=el.dataset.edgeType==='call';
    if(on){
        el.setAttribute('stroke-width','2.5');
        el.setAttribute('stroke',isCall?'#7db8f0':'#ff9090');
        el.setAttribute('marker-end',isCall?'url(#a-call-hl)':'url(#a-inh-hl)');
        // Move this edge to end of SVG so it's on top
        el.parentNode.appendChild(el);
    }else{
        el.setAttribute('stroke-width','1.5');
        el.setAttribute('stroke',isCall?'#5b9bd540':'#ff6b6b40');
        el.setAttribute('marker-end',isCall?'url(#a-call)':'url(#a-inh)');
        if(!isCall)el.setAttribute('stroke-dasharray','8,5');
    }
}

function isLockedConnected(el){
    if(!lockedId)return false;
    var s=el.dataset.source,t=el.dataset.target;
    return s===lockedId||t===lockedId||s.startsWith(lockedId+'.')||t.startsWith(lockedId+'.');
}

// ========== Block highlight ==========
function hlBlocks(){
    for(var i=0;i<arguments.length;i++){
        var id=arguments[i];
        var el=document.querySelector('[data-id="'+id+'"]');
        if(!el){var parts=id.split('.');for(var j=parts.length-1;j>0;j--){var c=parts.slice(0,j).join('.');el=document.querySelector('[data-id="'+c+'"]');if(el)break;}}
        if(el)el.classList.add('block-hl');
    }
}
function clearBlockHL(){document.querySelectorAll('.block-hl').forEach(function(e){e.classList.remove('block-hl');});}

// ========== Node hover -> highlight connected edges ==========
cvs.addEventListener('mouseover',function(e){
    var block=e.target.closest('[data-id]');
    if(!block)return;
    var id=block.dataset.id;
    highlightEdgesFor(id,true);
    hlBlocks(id);
});

cvs.addEventListener('mouseout',function(e){
    var block=e.target.closest('[data-id]');
    if(!block)return;
    var id=block.dataset.id;
    // Don't un-highlight if this block is locked
    if(id===lockedId)return;
    highlightEdgesFor(id,false);
    clearBlockHL();
    // Re-apply locked highlights
    if(lockedId){highlightEdgesFor(lockedId,true);hlBlocks(lockedId);}
});

// Click to lock / unlock
cvs.addEventListener('click',function(e){
    var block=e.target.closest('[data-id]');
    if(block){
        var id=block.dataset.id;
        if(lockedId===id){
            // Unlock
            lockedId=null;
            clearAllEdgeHL();
            clearBlockHL();
        }else{
            // Lock new
            if(lockedId){clearAllEdgeHL();clearBlockHL();}
            lockedId=id;
            highlightEdgesFor(id,true);
            hlBlocks(id);
        }
        e.stopPropagation();
        return;
    }
    // Click on empty area -> unlock
    if(lockedId){
        lockedId=null;
        clearAllEdgeHL();
        clearBlockHL();
    }
});

function highlightEdgesFor(id,on){
    var paths=svg.querySelectorAll('.e');
    for(var i=0;i<paths.length;i++){
        var p=paths[i];
        var s=p.dataset.source,t=p.dataset.target;
        var connected=s===id||t===id||s.startsWith(id+'.')||t.startsWith(id+'.');
        if(connected){
            highlightEdge(p,on);
            if(on)p.parentNode.appendChild(p); // bring to top within SVG
        }
    }
}

function clearAllEdgeHL(){
    var paths=svg.querySelectorAll('.e');
    for(var i=0;i<paths.length;i++)highlightEdge(paths[i],false);
}

// ========== Tooltip ==========
function showTip(e,text){tip.textContent=text;tip.style.display='block';tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+14)+'px';}
function hideTip(){tip.style.display='none';}

// ========== Pan & Zoom ==========
function updateTx(){cvs.style.transform='translate('+panX+'px,'+panY+'px) scale('+scale+')';zoomEl.textContent=Math.round(scale*100)+'%';}

ctnr.addEventListener('mousedown',function(e){
    if(e.target.closest('[data-id]')||e.target.closest('.e'))return;
    dragging=true;dsx=e.clientX;dsy=e.clientY;psx=panX;psy=panY;
    ctnr.classList.add('grabbing');
});
window.addEventListener('mousemove',function(e){if(!dragging)return;panX=psx+(e.clientX-dsx);panY=psy+(e.clientY-dsy);updateTx();});
window.addEventListener('mouseup',function(){dragging=false;ctnr.classList.remove('grabbing');});

ctnr.addEventListener('wheel',function(e){
    e.preventDefault();var d=e.deltaY>0?0.92:1.08;
    var ns=Math.max(0.12,Math.min(3,scale*d));
    var r=ctnr.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
    panX=mx-(mx-panX)*(ns/scale);panY=my-(my-panY)*(ns/scale);scale=ns;updateTx();
},{passive:false});

function fitToScreen(){
    var cr=ctnr.getBoundingClientRect(),pos=measure();
    var minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
    Object.keys(pos).forEach(function(id){var p=pos[id];minX=Math.min(minX,p.x);minY=Math.min(minY,p.y);maxX=Math.max(maxX,p.x+p.w);maxY=Math.max(maxY,p.y+p.h);});
    if(minX===Infinity)return;
    var cw=maxX-minX+100,ch=maxY-minY+100;
    scale=Math.min(cr.width/cw,cr.height/ch,1.0);scale=Math.max(0.12,scale);
    panX=(cr.width-cw*scale)/2-minX*scale+50*scale;
    panY=(cr.height-ch*scale)/2-minY*scale+50*scale;
    updateTx();
}

// ========== Toolbar ==========
document.getElementById('btn-fit').addEventListener('click',fitToScreen);

document.getElementById('btn-calls').addEventListener('click',function(){
    showCalls=!showCalls;this.classList.toggle('active',showCalls);requestAnimationFrame(drawEdges);
});
document.getElementById('btn-inherit').addEventListener('click',function(){
    showInherit=!showInherit;this.classList.toggle('active',showInherit);requestAnimationFrame(drawEdges);
});
document.getElementById('btn-top').addEventListener('click',function(){
    edgesOnTop=!edgesOnTop;this.classList.toggle('active',edgesOnTop);
    document.body.classList.toggle('edges-on-top',edgesOnTop);
});
document.getElementById('btn-collapse').addEventListener('click',function(){
    allCollapsed=!allCollapsed;this.classList.toggle('active',allCollapsed);
    document.querySelectorAll('.class-body,.class-params').forEach(function(e){e.style.display=allCollapsed?'none':'';});
    document.querySelectorAll('.func-signature,.method-signature').forEach(function(e){e.style.display=allCollapsed?'none':'';});
    setTimeout(function(){drawEdges();fitToScreen();},60);
});

// ========== Search ==========
var searchTimer;
document.getElementById('search-box').addEventListener('input',function(e){
    clearTimeout(searchTimer);
    searchTimer=setTimeout(function(){
        searchTerm=e.target.value.toLowerCase().trim();clearSearch();
        if(!searchTerm)return;
        document.querySelectorAll('[data-id]').forEach(function(el){
            var id=(el.dataset.id||'').toLowerCase(),txt=el.textContent.toLowerCase();
            if(id.indexOf(searchTerm)>=0||txt.indexOf(searchTerm)>=0)el.classList.add('search-hit');
        });
        var first=document.querySelector('.search-hit');
        if(first){var id=first.dataset.id,pos=measure(),p=pos[id];
            if(p){var cr=ctnr.getBoundingClientRect();panX=cr.width/2-p.cx*scale;panY=cr.height/2-p.cy*scale;updateTx();}}
    },200);
});
function clearSearch(){document.querySelectorAll('.search-hit').forEach(function(e){e.classList.remove('search-hit');});}

// ========== Keyboard ==========
document.addEventListener('keydown',function(e){
    if(e.target.id==='search-box'){if(e.key==='Escape'){e.target.blur();e.target.value='';searchTerm='';clearSearch();}return;}
    if(e.key==='f'||e.key==='F')fitToScreen();
    else if(e.key==='Escape'){document.getElementById('source-panel').classList.remove('open');clearSearch();document.getElementById('search-box').value='';searchTerm='';lockedId=null;clearAllEdgeHL();clearBlockHL();}
    else if(e.key==='/'||(e.ctrlKey&&e.key==='f')){e.preventDefault();document.getElementById('search-box').focus();}
});

buildAll();
})();
"""
