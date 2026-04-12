import { useState, useMemo, useCallback, useRef } from "react";

const RC = {head:"#5eead4",neck_shoulder:"#818cf8",torso:"#f59e0b",legs:"#fb923c",feet:"#f472b6"};
const BRC = ["#0d9488","#0891b2","#6366f1","#7c3aed","#a855f7","#d946ef","#ec4899","#f43f5e","#ef4444"];
const S = 68, CX = 115, PT = 6;
const hts = (dx,dy) => [CX+dx*S, PT+dy*S];

const Btn = ({on,onClick,children}) => (
  <button onClick={onClick} style={{background:on?"#1a2332":"transparent",border:`1px solid ${on?"#2d3f54":"#172030"}`,color:on?"#e0f2fe":"#3b5068",padding:"3px 8px",borderRadius:3,fontSize:10,cursor:"pointer",fontFamily:"inherit",transition:"all .12s"}}>{children}</button>
);
const Stat = ({label,value,unit,accent}) => (
  <div style={{display:"flex",justifyContent:"space-between",padding:"3px 0",borderBottom:"1px solid #0d1520"}}>
    <span style={{fontSize:9,color:"#3b5068"}}>{label}</span>
    <span style={{fontSize:9,color:accent||"#7dd3fc",fontWeight:600}}>{value}{unit&&<span style={{color:"#3b5068",fontWeight:400}}> {unit}</span>}</span>
  </div>
);
const Bar = ({label,value,max,color}) => (
  <div style={{display:"flex",alignItems:"center",gap:6,marginBottom:2}}>
    <span style={{fontSize:8,color:"#3b5068",width:70,flexShrink:0,textAlign:"right"}}>{label}</span>
    <div style={{flex:1,height:5,background:"#0a1018",borderRadius:2,overflow:"hidden"}}>
      <div style={{width:`${Math.min(100,(value/max)*100)}%`,height:"100%",background:color||"#0ea5e9",borderRadius:2}}/>
    </div>
    <span style={{fontSize:8,color:"#475569",width:32,textAlign:"right"}}>{(value*100).toFixed(1)}%</span>
  </div>
);

function normalize(raw) {
  const meta = raw.meta || {};
  const cls = meta.classification || {};
  const version = meta.schema_version || "unknown";
  const isV4 = !!raw.body_regions;

  // Contour mode: 180° (mirrored) or 360° (full).
  // When mirror.applied is true, only the right half (0..max-dy) is
  // authoritative — the left half is collapsed to dx≈0.  The renderer
  // must mirror the right half to build the bilateral silhouette.
  // When mirror.applied is false, the full contour is the actual
  // traced boundary and is used as-is.
  const contourRaw = raw.contour || [];
  const mirrored = meta.mirror?.applied !== false; // default to mirrored

  let splitIdx = 0;
  for (let i = 1; i < contourRaw.length; i++) {
    if (contourRaw[i][1] > contourRaw[splitIdx][1]) splitIdx = i;
  }

  let contour;
  if (mirrored) {
    // 180° mode: extract right half only, consumer mirrors
    const rightContour = contourRaw.slice(0, splitIdx + 1);
    contour = rightContour.filter((_,i) => i % 2 === 0 || i === rightContour.length - 1)
      .map(([dx,dy]) => [Math.round(dx*1000)/1000, Math.round(dy*1000)/1000]);
  } else {
    // 360° mode: use full contour as-is
    contour = contourRaw.filter((_,i) => i % 2 === 0 || i === contourRaw.length - 1)
      .map(([dx,dy]) => [Math.round(dx*1000)/1000, Math.round(dy*1000)/1000]);
  }

  // Strokes
  const strokes = (raw.strokes || []).map(s => {
    let pts = s.points || [];
    if (pts.length > 20) pts = pts.filter((_,i) => i % 2 === 0).concat([pts[pts.length-1]]);
    return { r: s.region, p: pts.map(([dx,dy]) => [Math.round(dx*1000)/1000, Math.round(dy*1000)/1000]) };
  });

  // Landmarks
  const landmarks = (raw.landmarks || []).map(l => ({
    n: l.name, d: l.description || "", dy: l.dy, dx: l.dx
  }));

  // Proportions
  const prop = raw.proportion || {};
  const pr = {
    hc: prop.head_count_total || prop.head_count_anatomical || 0,
    sr: prop.segment_ratios || {},
    wr: prop.width_ratios || {},
    comp: {},
    canons: []
  };
  if (prop.composite_ratios) {
    pr.comp = Object.fromEntries(Object.entries(prop.composite_ratios).filter(([k]) => k !== "note").map(([k,v]) => [k, typeof v === "number" ? Math.round(v*10000)/10000 : v]));
  }
  if (prop.canonical_comparisons) {
    pr.canons = prop.canonical_comparisons.map(c => ({ sys: c.system, heads: c.total_heads }));
  }

  // Body regions
  const br = isV4 ? (raw.body_regions.regions || []).map(r => ({ n: r.name, s: r.dy_start, e: r.dy_end })) : [];

  // Area profile
  const ar = isV4 && raw.area_profile ? (raw.area_profile.per_region || []).map(r => ({
    n: r.name, h: r.height_hu, a: r.area_hu2, f: r.area_fraction, mw: r.mean_full_width_hu
  })) : [];

  // Width profile
  const wp = isV4 && raw.width_profile ? (raw.width_profile.samples || []).filter((_,i) => i % 2 === 0).map(s => ({
    dy: s.dy, w: s.full_width
  })) : [];

  // Style deviation
  let sd = null;
  if (isV4 && raw.style_deviation) {
    const sdd = raw.style_deviation;
    sd = {
      canon: sdd.canon || "", fh: sdd.figure_head_count, ch: sdd.canon_head_count,
      l2: sdd.l2_stylisation_distance,
      pos: (sdd.position_deviations || []).map(p => ({ n: p.landmark, m: p.measured_fraction, c: p.canon_fraction, d: p.deviation })),
      wid: (sdd.width_deviations || []).map(w => ({ n: w.feature, m: w.measured, c: w.canon, d: w.deviation }))
    };
  }

  // Shape complexity
  let sc = null;
  if (isV4 && raw.shape_complexity) {
    sc = Object.fromEntries(Object.entries(raw.shape_complexity).filter(([k]) => !["note","reference"].includes(k)));
  }

  // Gesture line
  let gl = null;
  if (isV4 && raw.gesture_line) {
    const g = raw.gesture_line;
    gl = {
      lean: g.lean_angle_deg, li: g.lean_interpretation,
      cp: g.contrapposto_score, ci: g.contrapposto_interpretation,
      en: g.gesture_energy,
      ctr_dx: g.centroid?.dx || 0, ctr_dy: g.centroid?.dy || 0
    };
  }

  // Volumetric
  let vol = null;
  if (isV4 && raw.volumetric_estimates) {
    const v = raw.volumetric_estimates;
    vol = {
      cyl: v.cylindrical?.volume_hu3, ell: v.ellipsoidal?.volume_hu3, pap: v.pappus?.volume_hu3
    };
  }

  // Convex hull
  let hull = null;
  if (isV4 && raw.convex_hull) {
    const h = raw.convex_hull;
    hull = { sol: h.solidity, ha: h.hull_area_hu2, sa: h.silhouette_area_hu2, na: h.negative_space_area_hu2 };
  }

  // Biomechanics
  let bio = null;
  if (isV4 && raw.biomechanics) {
    const b = raw.biomechanics;
    bio = {
      hcm: b.canonical_height_cm, sc: b.scale_cm_per_hu,
      com_dy: b.whole_body_com?.dy, com_frac: b.whole_body_com?.dy_fraction
    };
  }

  // Medial axis
  let med = [];
  if (isV4 && raw.medial_axis?.main_axis?.samples) {
    med = raw.medial_axis.main_axis.samples.filter((_,i) => i % 4 === 0).map(p => ({
      dy: p.dy, r: p.inscribed_radius
    }));
  }

  // Interior holes from multi-span scanline measurements.
  // Where scanlines have 2+ spans at a given dy, the gap between spans
  // is an interior hole (e.g. the gap between separated legs).
  // Build hole polygons from consecutive multi-span levels.
  const holes = [];
  if (isV4 && raw.measurements?.scanlines) {
    const scanlines = raw.measurements.scanlines;
    const multiSpanLevels = [];
    for (const [dk, entry] of Object.entries(scanlines)) {
      let spans = null;
      if (typeof entry === "object" && !Array.isArray(entry) && entry.topology_detail) {
        spans = entry.topology_detail;
      } else if (Array.isArray(entry) && entry.length >= 2) {
        spans = entry;
      }
      // Only use levels with exactly 2 spans below the hip (dy > 4.0),
      // where the right span is on the positive side and left span is on
      // the negative side.  Levels above the hip with 2 spans are torso/
      // helmet detail crossings, not leg separation.
      const dy = parseFloat(dk);
      if (spans && spans.length === 2 && dy > 4.0 &&
          spans[0].inner_dx > 0 && spans[1].outer_dx < 0) {
        multiSpanLevels.push({
          dy: parseFloat(dk),
          gapLeft: spans[1].outer_dx,
          gapRight: spans[0].inner_dx,
        });
      }
    }
    multiSpanLevels.sort((a, b) => a.dy - b.dy);

    // Group consecutive levels into hole polygons
    if (multiSpanLevels.length >= 2) {
      let group = [multiSpanLevels[0]];
      for (let i = 1; i < multiSpanLevels.length; i++) {
        if (multiSpanLevels[i].dy - multiSpanLevels[i - 1].dy <= 0.25) {
          group.push(multiSpanLevels[i]);
        } else {
          if (group.length >= 2) holes.push(group);
          group = [multiSpanLevels[i]];
        }
      }
      if (group.length >= 2) holes.push(group);
    }
  }

  const surface = cls.surface?.label || "unknown";
  const gender = cls.gender?.label || "unknown";
  const view = cls.view?.label || "unknown";

  return { version, isV4, mirrored, contour, strokes, landmarks, pr, br, ar, wp, sd, sc, gl, vol, hull, bio, med, holes, surface, gender, view };
}

function Renderer({ data }) {
  const [layers, setLayers] = useState({contour:true,strokes:true,landmarks:true,regions:false,medial:false,widthViz:false});
  const [tab, setTab] = useState("proportions");
  const [hovLm, setHovLm] = useState(null);
  const toggle = useCallback(k => setLayers(p=>({...p,[k]:!p[k]})),[]);

  const D = data;
  const contourPath = useMemo(() => {
    let path;
    if (D.mirrored) {
      // 180° mode: mirror right half to build bilateral silhouette
      const r = D.contour.map(([dx,dy])=>hts(dx,dy));
      const l = [...D.contour].reverse().map(([dx,dy])=>hts(-dx,dy));
      path = "M "+[...r,...l].map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(" L ")+" Z";
    } else {
      // 360° mode: use full contour directly
      path = "M "+D.contour.map(([dx,dy])=>{const[x,y]=hts(dx,dy);return`${x.toFixed(1)},${y.toFixed(1)}`;}).join(" L ")+" Z";
    }

    // Append interior hole sub-paths from multi-span scanline data.
    // Each hole is a polygon tracing the gap between separated body parts
    // (e.g. the space between the legs). With fillRule="evenodd", these
    // sub-paths carve out the holes from the main silhouette fill.
    for (const hole of D.holes) {
      const rightEdge = hole.map(h => hts(h.gapRight, h.dy));
      const leftEdge = [...hole].reverse().map(h => hts(h.gapLeft, h.dy));
      path += " M "+[...rightEdge,...leftEdge].map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(" L ")+" Z";
    }
    return path;
  },[D.contour, D.mirrored, D.holes]);

  const lmData = useMemo(()=>D.landmarks.map(lm=>{
    const [xR,y]=hts(lm.dx,lm.dy);
    return {...lm,xR,y};
  }),[D.landmarks]);

  const neckLm = D.landmarks.find(l => l.n === "neck_valley");
  const neckDy = neckLm ? neckLm.dy : 1.26;

  const comDy = D.bio?.com_dy;
  const availLayers = [["contour","Contour"],["strokes","Strokes"],["landmarks","Landmarks"]];
  if (D.br.length) availLayers.push(["regions","Regions"]);
  if (D.med.length) availLayers.push(["medial","Medial"]);
  if (D.wp.length) availLayers.push(["widthViz","Width"]);

  const tabs = [["proportions","Proportions"]];
  if (D.ar.length) tabs.push(["area","Area"]);
  if (D.sd) tabs.push(["style","Style Dev"]);
  if (D.sc || D.gl) tabs.push(["shape","Shape"]);
  if (D.bio) tabs.push(["bio","Biomech"]);
  if (D.hull || D.vol) tabs.push(["hull","Hull/Vol"]);

  return (
    <>
      {/* Header */}
      <div style={{width:"100%",maxWidth:720,borderBottom:"1px solid #0f1d2d",paddingBottom:8,marginBottom:8}}>
        <div style={{display:"flex",alignItems:"baseline",gap:10,flexWrap:"wrap"}}>
          <span style={{color:"#e0f2fe",fontSize:14,fontWeight:700,letterSpacing:2}}>SILHOUETTE ANALYSIS</span>
          <span style={{fontSize:9,color:"#1e3a5f",letterSpacing:.6}}>
            {D.version} · {D.view.toUpperCase()} · {D.surface.toUpperCase()} · {D.gender.toUpperCase()} · {D.pr.hc.toFixed(1)} HU
          </span>
        </div>
        <div style={{fontSize:9,color:"#172030",marginTop:2}}>
          {D.contour.length} contour pts · {D.strokes.length} strokes · {D.landmarks.length} landmarks
          {D.br.length ? ` · ${D.br.length} regions` : ""}
          {D.hull ? ` · solidity ${D.hull.sol}` : ""}
        </div>
      </div>

      {/* Layers */}
      <div style={{display:"flex",gap:4,flexWrap:"wrap",marginBottom:8,maxWidth:720,width:"100%"}}>
        {availLayers.map(([k,lb])=><Btn key={k} on={layers[k]} onClick={()=>toggle(k)}>{lb}</Btn>)}
      </div>

      {/* SVG */}
      <svg viewBox="0 0 270 560" style={{width:"100%",maxWidth:420,height:"auto"}}>
        <defs>
          <linearGradient id="cf" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#5eead4" stopOpacity=".04"/>
            <stop offset="50%" stopColor="#818cf8" stopOpacity=".03"/>
            <stop offset="100%" stopColor="#f472b6" stopOpacity=".04"/>
          </linearGradient>
          <filter id="gl"><feGaussianBlur stdDeviation="1.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>
        {Array.from({length:9},(_,i)=>{
          const y=PT+i*S;
          return <g key={i}><line x1={0} y1={y} x2={270} y2={y} stroke="#0d1520" strokeWidth={.3} strokeDasharray="2,4"/><text x={2} y={y-1} fill="#0d1520" fontSize={5} fontFamily="inherit">{i}.0</text></g>;
        })}
        <line x1={CX} y1={0} x2={CX} y2={560} stroke="#172030" strokeWidth={.3} strokeDasharray="1,3"/>

        {layers.regions && D.br.map((r,i)=><rect key={i} x={CX-1.4*S} y={PT+r.s*S} width={2.8*S} height={(r.e-r.s)*S} fill={BRC[i%BRC.length]} fillOpacity={.06} stroke={BRC[i%BRC.length]} strokeWidth={.3} strokeOpacity={.2}/>)}
        {layers.regions && D.br.map((r,i)=><text key={`t${i}`} x={4} y={PT+(r.s+r.e)/2*S+2} fill={BRC[i%BRC.length]} fontSize={5} fontFamily="inherit" opacity={.5}>{r.n}</text>)}

        {layers.widthViz && D.wp.filter(w=>w.w>0&&w.w<3).map((w,i)=>{
          const y=PT+w.dy*S, hw=w.w/2*S;
          return <line key={i} x1={CX-hw} y1={y} x2={CX+hw} y2={y} stroke="#0ea5e9" strokeWidth={.4} opacity={.25}/>;
        })}

        {layers.medial && D.med.filter(m=>m.r>0).map((m,i)=>(
          <circle key={i} cx={CX} cy={PT+m.dy*S} r={Math.max(.5,m.r*S*.08)} fill="#f59e0b" fillOpacity={.3}/>
        ))}

        {layers.contour && <g>
          <path d={contourPath} fill="url(#cf)" fillRule="evenodd"/>
          <path d={contourPath} fill="none" stroke="#334155" strokeWidth={.7} strokeLinejoin="round"/>
        </g>}

        {layers.strokes && D.strokes.map((sp,i)=>{
          const d="M "+sp.p.map(([dx,dy])=>{const[x,y]=hts(dx,dy);return`${x.toFixed(1)},${y.toFixed(1)}`;}).join(" L ");
          return <path key={i} d={d} fill="none" stroke={RC[sp.r]||"#64748b"} strokeWidth={.5} opacity={.55} strokeLinecap="round" strokeLinejoin="round"/>;
        })}

        {layers.landmarks && lmData.map((lm,i)=>{
          const hov=hovLm===lm.n;
          return <g key={i} onMouseEnter={()=>setHovLm(lm.n)} onMouseLeave={()=>setHovLm(null)} style={{cursor:"pointer"}}>
            <line x1={CX-2} y1={lm.y} x2={CX+2} y2={lm.y} stroke={hov?"#e0f2fe":"#3b5068"} strokeWidth={hov?1:.5}/>
            <circle cx={lm.xR} cy={lm.y} r={hov?2:1.2} fill={hov?"#7dd3fc":"#3b5068"} filter={hov?"url(#gl)":undefined}/>
            <text x={260} y={lm.y+2} fill={hov?"#bae6fd":"#1e3a5f"} fontSize={hov?6:5} fontFamily="inherit" textAnchor="end" fontWeight={hov?700:400}>
              {lm.n.replace(/_/g," ").slice(0,14)}
            </text>
            {hov&&<g>
              <rect x={90} y={lm.y-16} width={160} height={12} rx={2} fill="#0f1d2d" stroke="#1e3a5f" strokeWidth={.4}/>
              <text x={94} y={lm.y-8} fill="#7dd3fc" fontSize={4.5} fontFamily="inherit">{lm.d.slice(0,50)} — dy:{lm.dy.toFixed(3)} dx:{lm.dx.toFixed(3)}</text>
            </g>}
          </g>;
        })}

        {comDy != null && <g>
          <line x1={CX-4} y1={PT+comDy*S} x2={CX+4} y2={PT+comDy*S} stroke="#ef4444" strokeWidth={.8} strokeDasharray="1,1"/>
          <text x={CX+6} y={PT+comDy*S+2} fill="#ef4444" fontSize={4.5} fontFamily="inherit">CoM</text>
        </g>}

        {Array.from({length:Math.min(8, Math.ceil(D.pr.hc))},(_,i)=>{
          const y1=PT+.005*S+i*neckDy*S, y2=y1+neckDy*S;
          if (i >= Math.ceil(D.pr.hc)) return null;
          return <g key={i}>
            <rect x={4} y={y1} width={8} height={neckDy*S} fill={i%2===0?"rgba(94,234,212,.06)":"rgba(129,140,248,.06)"} stroke="#172030" strokeWidth={.2}/>
            <text x={8} y={(y1+y2)/2+2} fill="#1e3a5f" fontSize={4.5} fontFamily="inherit" textAnchor="middle">{i+1}</text>
          </g>;
        })}
      </svg>

      {/* Tabs */}
      <div style={{display:"flex",gap:2,marginTop:12,maxWidth:720,width:"100%",borderBottom:"1px solid #0f1d2d",flexWrap:"wrap"}}>
        {tabs.map(([k,lb])=>(
          <button key={k} onClick={()=>setTab(k)} style={{background:tab===k?"#0f1d2d":"transparent",border:"none",borderBottom:tab===k?"2px solid #0ea5e9":"2px solid transparent",color:tab===k?"#7dd3fc":"#1e3a5f",padding:"5px 10px",fontSize:10,cursor:"pointer",fontFamily:"inherit",fontWeight:tab===k?600:400}}>{lb}</button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{maxWidth:720,width:"100%",padding:"12px 0"}}>
        {tab==="proportions"&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>SEGMENT RATIOS — {D.pr.hc.toFixed(1)} HEAD UNITS</div>
          {Object.entries(D.pr.sr).map(([k,v])=><Bar key={k} label={k.split("→").map(s=>s.slice(0,4)).join("→")} value={v} max={.3} color="#0ea5e9"/>)}
          {Object.keys(D.pr.comp).length > 0 && <>
            <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>COMPOSITE RATIOS</div>
            {Object.entries(D.pr.comp).map(([k,v])=><Stat key={k} label={k.replace(/_/g," ")} value={typeof v==="number"?v.toFixed(3):String(v)}/>)}
          </>}
          {D.pr.canons.length > 0 && <>
            <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:6,letterSpacing:1}}>CANONICAL SYSTEMS</div>
            {D.pr.canons.map((c,i)=><Stat key={i} label={c.sys} value={`${c.heads} heads`} accent="#f59e0b"/>)}
          </>}
        </div>}

        {tab==="area"&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>AREA PER BODY REGION (HU²)</div>
          {D.ar.map((r,i)=>(
            <div key={i} style={{display:"flex",alignItems:"center",gap:6,marginBottom:3}}>
              <div style={{width:8,height:8,borderRadius:2,background:BRC[i%BRC.length],opacity:.7}}/>
              <span style={{fontSize:9,color:"#3b5068",width:80}}>{r.n}</span>
              <div style={{flex:1,height:6,background:"#0a1018",borderRadius:2,overflow:"hidden"}}>
                <div style={{width:`${r.f*100*4.5}%`,height:"100%",background:BRC[i%BRC.length],opacity:.7,borderRadius:2}}/>
              </div>
              <span style={{fontSize:8,color:"#64748b",width:55,textAlign:"right"}}>{r.a.toFixed(2)} ({(r.f*100).toFixed(1)}%)</span>
            </div>
          ))}
        </div>}

        {tab==="style"&&D.sd&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:4,letterSpacing:1}}>STYLE DEVIATION vs {(D.sd.canon||"").replace(/_/g," ").toUpperCase()}</div>
          <div style={{fontSize:8,color:"#1e3a5f",marginBottom:10}}>Figure: {D.sd.fh} heads · Canon: {D.sd.ch} heads · L²: {D.sd.l2}</div>
          <div style={{fontSize:9,color:"#3b5068",fontWeight:600,marginBottom:6}}>POSITION DEVIATIONS</div>
          {D.sd.pos.map((p,i)=>(
            <div key={i} style={{display:"flex",alignItems:"center",gap:8,marginBottom:3}}>
              <span style={{fontSize:8,color:"#3b5068",width:80}}>{p.n.replace(/_/g," ")}</span>
              <div style={{flex:1,height:8,background:"#0a1018",borderRadius:3,position:"relative",overflow:"hidden"}}>
                <div style={{position:"absolute",left:"50%",top:0,bottom:0,width:1,background:"#1e3a5f"}}/>
                <div style={{position:"absolute",left:`${50+p.d*500}%`,top:1,width:6,height:6,borderRadius:3,background:p.d>0?"#f59e0b":"#0ea5e9",transform:"translateX(-3px)"}}/>
              </div>
              <span style={{fontSize:8,color:p.d>0?"#f59e0b":"#0ea5e9",width:40,textAlign:"right"}}>{p.d>0?"+":""}{(p.d*100).toFixed(1)}%</span>
            </div>
          ))}
          <div style={{fontSize:9,color:"#3b5068",fontWeight:600,marginTop:12,marginBottom:6}}>WIDTH DEVIATIONS</div>
          {D.sd.wid.map((w,i)=>(
            <div key={i} style={{display:"flex",alignItems:"center",gap:8,marginBottom:3}}>
              <span style={{fontSize:8,color:"#3b5068",width:80}}>{w.n.replace(/_/g," ")}</span>
              <div style={{flex:1,height:8,background:"#0a1018",borderRadius:3,position:"relative",overflow:"hidden"}}>
                <div style={{position:"absolute",left:"50%",top:0,bottom:0,width:1,background:"#1e3a5f"}}/>
                <div style={{position:"absolute",left:`${50+w.d*300}%`,top:1,width:6,height:6,borderRadius:3,background:w.d>0?"#f59e0b":"#0ea5e9",transform:"translateX(-3px)"}}/>
              </div>
              <span style={{fontSize:8,color:w.d>0?"#f59e0b":"#0ea5e9",width:40,textAlign:"right"}}>{w.d>0?"+":""}{(w.d*100).toFixed(1)}%</span>
            </div>
          ))}
        </div>}

        {tab==="shape"&&<div>
          {D.sc && <>
            <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>SHAPE COMPLEXITY</div>
            {Object.entries(D.sc).map(([k,v])=>(
              <Stat key={k} label={k.replace(/_/g," ")} value={typeof v==="object"?v.value:v} unit={typeof v==="object"?v.units||v.method||"":""}/>
            ))}
          </>}
          {D.gl && <>
            <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>GESTURE LINE</div>
            <Stat label="Lean Angle" value={`${D.gl.lean}°`} unit={(D.gl.li||"").replace(/_/g," ")}/>
            <Stat label="Contrapposto" value={D.gl.cp} unit={D.gl.ci} accent="#a78bfa"/>
            <Stat label="Gesture Energy" value={D.gl.en}/>
            <Stat label="Centroid" value={`(${D.gl.ctr_dx}, ${D.gl.ctr_dy})`} unit="HU"/>
          </>}
        </div>}

        {tab==="bio"&&D.bio&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>BIOMECHANICS</div>
          <Stat label="Canonical Height" value={D.bio.hcm} unit="cm"/>
          <Stat label="Scale Factor" value={D.bio.sc} unit="cm/HU"/>
          {D.bio.com_dy!=null&&<Stat label="Center of Mass" value={D.bio.com_dy.toFixed(3)} unit="HU"/>}
          {D.bio.com_frac!=null&&<Stat label="CoM Fraction" value={(D.bio.com_frac*100).toFixed(1)} unit="% from crown"/>}
          {D.wp.length>0&&<>
            <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>WIDTH PROFILE</div>
            <svg viewBox="0 0 300 100" style={{width:"100%",height:80,background:"#0a1018",borderRadius:4}}>
              {D.wp.filter(w=>w.w>0&&w.w<3).map((w,i)=>{
                const x=w.dy/8*290+5, h=w.w/2.5*90;
                return <rect key={i} x={x} y={95-h} width={3} height={h} fill="#0ea5e9" opacity={.5} rx={1}/>;
              })}
              <text x={5} y={10} fill="#1e3a5f" fontSize={6} fontFamily="inherit">Full Width (HU)</text>
            </svg>
          </>}
          {D.med.length>0&&<>
            <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>MEDIAL AXIS INSCRIBED RADIUS</div>
            <svg viewBox="0 0 300 60" style={{width:"100%",height:50,background:"#0a1018",borderRadius:4}}>
              <polyline fill="none" stroke="#f59e0b" strokeWidth={1} opacity={.6} points={D.med.filter(m=>m.r>0).map(m=>`${m.dy/8*290+5},${55-m.r/1.3*45}`).join(" ")}/>
              <text x={5} y={10} fill="#1e3a5f" fontSize={6} fontFamily="inherit">Inscribed Radius (HU)</text>
            </svg>
          </>}
        </div>}

        {tab==="hull"&&<div>
          {D.hull&&<>
            <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>CONVEX HULL</div>
            <Stat label="Solidity" value={D.hull.sol} unit="A/A_hull"/>
            <Stat label="Hull Area" value={D.hull.ha} unit="HU²"/>
            <Stat label="Silhouette Area" value={D.hull.sa} unit="HU²"/>
            <Stat label="Negative Space" value={D.hull.na} unit="HU²" accent="#ef4444"/>
          </>}
          {D.vol&&<>
            <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>VOLUMETRIC ESTIMATES (HU³)</div>
            {D.vol.cyl!=null&&<Stat label="Cylindrical (π∫dx²dy)" value={D.vol.cyl} accent="#0ea5e9"/>}
            {D.vol.ell!=null&&<Stat label="Ellipsoidal (π/4∫dx²dy)" value={D.vol.ell} accent="#818cf8"/>}
            {D.vol.pap!=null&&<Stat label="Pappus (2π∫x·w·dy)" value={D.vol.pap} accent="#f59e0b"/>}
          </>}
        </div>}
      </div>
    </>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [fileName, setFileName] = useState("");
  const fileRef = useRef(null);

  const loadFile = useCallback((file) => {
    setError(null);
    if (!file) return;
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const raw = JSON.parse(e.target.result);
        if (!raw.contour || !Array.isArray(raw.contour)) {
          setError("Invalid JSON: missing 'contour' array.");
          return;
        }
        const normalized = normalize(raw);
        setData(normalized);
      } catch (err) {
        setError(`Parse error: ${err.message}`);
      }
    };
    reader.onerror = () => setError("Failed to read file.");
    reader.readAsText(file);
  }, []);

  const onDrop = useCallback((e) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) loadFile(file);
  }, [loadFile]);

  const onDrag = useCallback((e) => { e.preventDefault(); setDragging(true); }, []);
  const onDragLeave = useCallback(() => setDragging(false), []);

  return (
    <div style={{background:"#060b12",minHeight:"100vh",fontFamily:"'IBM Plex Mono','Fira Code',monospace",color:"#64748b",padding:"12px 8px",display:"flex",flexDirection:"column",alignItems:"center"}}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700&display=swap');`}</style>

      {!data ? (
        <div
          onDrop={onDrop} onDragOver={onDrag} onDragLeave={onDragLeave}
          onClick={() => fileRef.current?.click()}
          style={{
            width:"100%",maxWidth:500,marginTop:"15vh",
            border:`2px dashed ${dragging?"#0ea5e9":"#1e3a5f"}`,
            borderRadius:12,padding:"60px 30px",textAlign:"center",
            cursor:"pointer",transition:"all .2s",
            background:dragging?"rgba(14,165,233,.04)":"transparent"
          }}
        >
          <input ref={fileRef} type="file" accept=".json" style={{display:"none"}} onChange={e=>loadFile(e.target.files?.[0])}/>
          <div style={{fontSize:32,marginBottom:12,opacity:.3}}>⬆</div>
          <div style={{color:"#e0f2fe",fontSize:14,fontWeight:700,letterSpacing:2,marginBottom:8}}>SILHOUETTE ANALYSIS</div>
          <div style={{color:"#3b5068",fontSize:11,marginBottom:16}}>
            Drop a contour JSON (v2 or v4) here, or click to browse
          </div>
          <div style={{color:"#172030",fontSize:9}}>
            Expects schema with: contour, landmarks, proportion, strokes
            {" "}— v4 adds: body_regions, biomechanics, style_deviation, shape_complexity, volumetric_estimates, convex_hull
          </div>
          {error && <div style={{color:"#ef4444",fontSize:10,marginTop:16,padding:"8px 12px",background:"rgba(239,68,68,.08)",borderRadius:6}}>{error}</div>}
        </div>
      ) : (
        <>
          <div style={{width:"100%",maxWidth:720,display:"flex",justifyContent:"space-between",alignItems:"center",marginBottom:4}}>
            <span style={{fontSize:9,color:"#1e3a5f"}}>{fileName}</span>
            <button onClick={()=>{setData(null);setFileName("");setError(null);}} style={{background:"transparent",border:"1px solid #172030",color:"#3b5068",padding:"2px 8px",borderRadius:3,fontSize:9,cursor:"pointer",fontFamily:"inherit"}}>Load Another</button>
          </div>
          <Renderer data={data}/>
          <div style={{fontSize:7,color:"#0d1520",marginTop:16,textAlign:"center"}}>
            schema {data.version} · {data.contour.length} pts · {data.strokes.length} strokes · {data.landmarks.length} landmarks
          </div>
        </>
      )}
    </div>
  );
}
