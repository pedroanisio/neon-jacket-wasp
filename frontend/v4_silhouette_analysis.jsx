import { useState, useMemo, useCallback } from "react";
import V4FileLoader from "./V4FileLoader.jsx";


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
      <div style={{width:`${(value/max)*100}%`,height:"100%",background:color||"#0ea5e9",borderRadius:2,transition:"width .3s"}}/>
    </div>
    <span style={{fontSize:8,color:"#475569",width:32,textAlign:"right"}}>{(value*100).toFixed(1)}%</span>
  </div>
);

export default function V4Renderer() {
  const [loaded, setLoaded] = useState(null);

  if (!loaded) {
    return (
      <div style={{ background: "#060b12", minHeight: "100vh", padding: "16px 8px",
        fontFamily: "'IBM Plex Mono','Fira Code',monospace" }}>
        <V4FileLoader title="V4 ANALYSIS" description="Drop a silhouette v4 JSON for full analysis dashboard" onLoad={setLoaded} />
      </div>
    );
  }

  return <V4RendererInner D={loaded.data} fileName={loaded.fileName} onReset={() => setLoaded(null)} />;
}

function V4RendererInner({ D, fileName, onReset }) {
  const [layers, setLayers] = useState({contour:true,strokes:true,landmarks:true,regions:false,medial:false,widthViz:false});
  const [tab, setTab] = useState("proportions");
  const [hovLm, setHovLm] = useState(null);
  const toggle = useCallback(k => setLayers(p=>({...p,[k]:!p[k]})),[]);

  const contourPath = useMemo(() => {
    const r = D.c.map(([dx,dy])=>hts(dx,dy));
    const l = [...D.c].reverse().map(([dx,dy])=>hts(-dx,dy));
    return "M "+[...r,...l].map(([x,y])=>`${x.toFixed(1)},${y.toFixed(1)}`).join(" L ")+" Z";
  },[]);

  const lmData = useMemo(()=>D.l.map(lm=>{
    const [xR,y]=hts(lm.dx,lm.dy);
    return {...lm,xR,y};
  }),[]);

  const neckDy = D.l[3].dy; // neck_valley = 1 HU

  return (
    <div style={{background:"#060b12",minHeight:"100vh",fontFamily:"'IBM Plex Mono','Fira Code',monospace",color:"#64748b",padding:"12px 8px",display:"flex",flexDirection:"column",alignItems:"center"}}>
      <style>{`@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600;700&display=swap');`}</style>

      {/* Header */}
      <div style={{width:"100%",maxWidth:720,borderBottom:"1px solid #0f1d2d",paddingBottom:8,marginBottom:8}}>
        <div style={{display:"flex",alignItems:"baseline",gap:10,flexWrap:"wrap"}}>
          <span style={{color:"#e0f2fe",fontSize:14,fontWeight:700,letterSpacing:2}}>SILHOUETTE ANALYSIS</span>
          <span style={{fontSize:9,color:"#1e3a5f",letterSpacing:.6}}>{D.version} · {D.view.toUpperCase()} · {D.surface.toUpperCase()} · {D.gender.toUpperCase()} · {D.pr.hc.toFixed(1)} HU</span>
        </div>
        <div style={{fontSize:9,color:"#172030",marginTop:2}}>{D.c.length} contour pts · 50 strokes · {D.l.length} landmarks · {D.ar.length} body regions · solidity {D.hull.sol}</div>
      </div>

      {/* Layer toggles */}
      <div style={{display:"flex",gap:4,flexWrap:"wrap",marginBottom:8,maxWidth:720,width:"100%"}}>
        {[["contour","Contour"],["strokes","Strokes"],["landmarks","Landmarks"],["regions","Regions"],["medial","Medial"],["widthViz","Width"]].map(([k,lb])=>(
          <Btn key={k} on={layers[k]} onClick={()=>toggle(k)}>{lb}</Btn>
        ))}
      </div>

      {/* Main SVG */}
      <svg viewBox={`0 0 270 560`} style={{width:"100%",maxWidth:420,height:"auto"}}>
        <defs>
          <linearGradient id="cf" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#5eead4" stopOpacity=".04"/>
            <stop offset="50%" stopColor="#818cf8" stopOpacity=".03"/>
            <stop offset="100%" stopColor="#f472b6" stopOpacity=".04"/>
          </linearGradient>
          <filter id="gl"><feGaussianBlur stdDeviation="1.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>

        {/* Grid */}
        {Array.from({length:9},(_,i)=>{
          const y=PT+i*S;
          return <g key={i}><line x1={0} y1={y} x2={270} y2={y} stroke="#0d1520" strokeWidth={.3} strokeDasharray="2,4"/><text x={2} y={y-1} fill="#0d1520" fontSize={5} fontFamily="inherit">{i}.0</text></g>;
        })}
        <line x1={CX} y1={0} x2={CX} y2={560} stroke="#172030" strokeWidth={.3} strokeDasharray="1,3"/>

        {/* Body region bands */}
        {layers.regions && D.br.map((r,i)=>(
          <rect key={i} x={CX-1.4*S} y={PT+r.s*S} width={2.8*S} height={(r.e-r.s)*S} fill={BRC[i]} fillOpacity={.06} stroke={BRC[i]} strokeWidth={.3} strokeOpacity={.2}/>
        ))}
        {layers.regions && D.br.map((r,i)=>(
          <text key={`t${i}`} x={4} y={PT+(r.s+r.e)/2*S+2} fill={BRC[i]} fontSize={5} fontFamily="inherit" opacity={.5}>{r.n}</text>
        ))}

        {/* Width visualization */}
        {layers.widthViz && D.wp.filter(w=>w.w>0&&w.w<3).map((w,i)=>{
          const y=PT+w.dy*S;
          const hw=w.w/2*S;
          return <line key={i} x1={CX-hw} y1={y} x2={CX+hw} y2={y} stroke="#0ea5e9" strokeWidth={.4} opacity={.25}/>;
        })}

        {/* Medial axis */}
        {layers.medial && D.med.filter(m=>m.r>0).map((m,i)=>(
          <circle key={i} cx={CX} cy={PT+m.dy*S} r={Math.max(.5,m.r*S*.08)} fill="#f59e0b" fillOpacity={.3}/>
        ))}

        {/* Contour */}
        {layers.contour && <g>
          <path d={contourPath} fill="url(#cf)"/>
          <path d={contourPath} fill="none" stroke="#334155" strokeWidth={.7} strokeLinejoin="round"/>
        </g>}

        {/* Landmarks */}
        {layers.landmarks && lmData.map((lm,i)=>{
          const hov=hovLm===lm.n;
          return <g key={i} onMouseEnter={()=>setHovLm(lm.n)} onMouseLeave={()=>setHovLm(null)} style={{cursor:"pointer"}}>
            <line x1={CX-2} y1={lm.y} x2={CX+2} y2={lm.y} stroke={hov?"#e0f2fe":"#3b5068"} strokeWidth={hov?1:.5}/>
            <circle cx={lm.xR} cy={lm.y} r={hov?2:1.2} fill={hov?"#7dd3fc":"#3b5068"} filter={hov?"url(#gl)":undefined}/>
            <text x={260} y={lm.y+2} fill={hov?"#bae6fd":"#1e3a5f"} fontSize={hov?6:5} fontFamily="inherit" textAnchor="end" fontWeight={hov?700:400}>{lm.n.replace(/_/g," ").slice(0,12)}</text>
            {hov&&<g>
              <rect x={100} y={lm.y-16} width={150} height={12} rx={2} fill="#0f1d2d" stroke="#1e3a5f" strokeWidth={.4}/>
              <text x={104} y={lm.y-8} fill="#7dd3fc" fontSize={4.5} fontFamily="inherit">{lm.d} — dy:{lm.dy.toFixed(3)} dx:{lm.dx.toFixed(3)}</text>
            </g>}
          </g>;
        })}

        {/* CoM marker */}
        <g>
          <line x1={CX-4} y1={PT+D.bio.com_dy*S} x2={CX+4} y2={PT+D.bio.com_dy*S} stroke="#ef4444" strokeWidth={.8} strokeDasharray="1,1"/>
          <text x={CX+6} y={PT+D.bio.com_dy*S+2} fill="#ef4444" fontSize={4.5} fontFamily="inherit">CoM</text>
        </g>

        {/* HU ruler */}
        {Array.from({length:7},(_,i)=>{
          const y1=PT+D.l[0].dy*S+i*neckDy*S;
          const y2=y1+neckDy*S;
          return <g key={i}>
            <rect x={4} y={y1} width={8} height={neckDy*S} fill={i%2===0?"rgba(94,234,212,.06)":"rgba(129,140,248,.06)"} stroke="#172030" strokeWidth={.2}/>
            <text x={8} y={(y1+y2)/2+2} fill="#1e3a5f" fontSize={4.5} fontFamily="inherit" textAnchor="middle">{i+1}</text>
          </g>;
        })}
      </svg>

      {/* Tab bar */}
      <div style={{display:"flex",gap:2,marginTop:12,maxWidth:720,width:"100%",borderBottom:"1px solid #0f1d2d",paddingBottom:0,flexWrap:"wrap"}}>
        {[["proportions","Proportions"],["area","Area"],["style","Style Dev"],["shape","Shape"],["bio","Biomech"],["hull","Hull/Vol"]].map(([k,lb])=>(
          <button key={k} onClick={()=>setTab(k)} style={{background:tab===k?"#0f1d2d":"transparent",border:"none",borderBottom:tab===k?"2px solid #0ea5e9":"2px solid transparent",color:tab===k?"#7dd3fc":"#1e3a5f",padding:"5px 10px",fontSize:10,cursor:"pointer",fontFamily:"inherit",fontWeight:tab===k?600:400}}>{lb}</button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{maxWidth:720,width:"100%",padding:"12px 0"}}>
        {tab==="proportions"&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>SEGMENT RATIOS — {D.pr.hc.toFixed(1)} HEAD UNITS</div>
          {Object.entries(D.pr.sr).map(([k,v])=><Bar key={k} label={k.split("→").map(s=>s.slice(0,4)).join("→")} value={v} max={.3} color="#0ea5e9"/>)}
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>COMPOSITE RATIOS</div>
          {Object.entries(D.pr.comp).map(([k,v])=><Stat key={k} label={k.replace(/_/g," ")} value={v.toFixed(3)}/>)}
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:6,letterSpacing:1}}>CANONICAL SYSTEMS</div>
          {D.pr.canons.map((c,i)=><Stat key={i} label={c.sys} value={`${c.heads} heads`} accent="#f59e0b"/>)}
        </div>}

        {tab==="area"&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>AREA PER BODY REGION (HU²)</div>
          {D.ar.map((r,i)=>(
            <div key={i} style={{display:"flex",alignItems:"center",gap:6,marginBottom:3}}>
              <div style={{width:8,height:8,borderRadius:2,background:BRC[i],opacity:.7}}/>
              <span style={{fontSize:9,color:"#3b5068",width:80}}>{r.n}</span>
              <div style={{flex:1,height:6,background:"#0a1018",borderRadius:2,overflow:"hidden"}}>
                <div style={{width:`${r.f*100*4.5}%`,height:"100%",background:BRC[i],opacity:.7,borderRadius:2}}/>
              </div>
              <span style={{fontSize:8,color:"#64748b",width:55,textAlign:"right"}}>{r.a.toFixed(2)} ({(r.f*100).toFixed(1)}%)</span>
            </div>
          ))}
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>REGION METRICS</div>
          {D.ar.map((r,i)=>(
            <div key={i} style={{display:"flex",gap:12,fontSize:8,color:"#3b5068",padding:"2px 0",borderBottom:"1px solid #0a1018"}}>
              <span style={{width:80,color:BRC[i]}}>{r.n}</span>
              <span>h={r.h.toFixed(2)}</span>
              <span>w̄={r.mw.toFixed(2)}</span>
              <span>A={r.a.toFixed(2)}</span>
            </div>
          ))}
        </div>}

        {tab==="style"&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:4,letterSpacing:1}}>STYLE DEVIATION vs {D.sd.canon.replace(/_/g," ").toUpperCase()}</div>
          <div style={{fontSize:8,color:"#1e3a5f",marginBottom:10}}>Figure: {D.sd.fh} heads · Canon: {D.sd.ch} heads · L² distance: {D.sd.l2}</div>
          <div style={{fontSize:9,color:"#3b5068",fontWeight:600,marginBottom:6}}>POSITION DEVIATIONS (fraction of height)</div>
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
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>SHAPE COMPLEXITY</div>
          <Stat label="Curvature Entropy" value={D.sc.curvature_entropy.value} unit="bits"/>
          <Stat label="Fractal Dimension" value={D.sc.fractal_dimension.value} unit="(1.0=smooth)"/>
          <Stat label="Compactness" value={D.sc.compactness.value} unit="(circle=1.0)"/>
          <Stat label="Rectangularity" value={D.sc.rectangularity.value} unit="A/A_bbox"/>
          <Stat label="Eccentricity" value={D.sc.eccentricity.value} unit="(0=circle)"/>
          <Stat label="Roughness" value={D.sc.roughness.value} unit="P/P_hull"/>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>GESTURE LINE</div>
          <Stat label="Lean Angle" value={`${D.gl.lean}°`} unit={D.gl.li.replace(/_/g," ")}/>
          <Stat label="Contrapposto" value={D.gl.cp} unit={D.gl.ci} accent="#a78bfa"/>
          <Stat label="Gesture Energy" value={D.gl.en}/>
          <Stat label="Centroid" value={`(${D.gl.ctr_dx}, ${D.gl.ctr_dy})`} unit="HU"/>
        </div>}

        {tab==="bio"&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>BIOMECHANICS</div>
          <Stat label="Canonical Height" value={D.bio.hcm} unit="cm"/>
          <Stat label="Scale Factor" value={D.bio.sc} unit="cm/HU"/>
          <Stat label="Center of Mass (dy)" value={D.bio.com_dy.toFixed(3)} unit="HU"/>
          <Stat label="CoM Fraction" value={(D.bio.com_frac*100).toFixed(1)} unit="% from crown"/>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>WIDTH PROFILE (clean samples)</div>
          <svg viewBox="0 0 300 100" style={{width:"100%",height:80,background:"#0a1018",borderRadius:4}}>
            {D.wp.filter(w=>w.w>0&&w.w<3).map((w,i)=>{
              const x=w.dy/8*290+5;
              const h=w.w/2.5*90;
              return <rect key={i} x={x} y={95-h} width={3} height={h} fill="#0ea5e9" opacity={.5} rx={1}/>;
            })}
            <text x={5} y={10} fill="#1e3a5f" fontSize={6} fontFamily="inherit">Full Width (HU)</text>
            {[0,2,4,6,8].map(v=><text key={v} x={v/8*290+5} y={98} fill="#0d1520" fontSize={5} fontFamily="inherit">{v}</text>)}
          </svg>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>MEDIAL AXIS INSCRIBED RADIUS</div>
          <svg viewBox="0 0 300 60" style={{width:"100%",height:50,background:"#0a1018",borderRadius:4}}>
            <polyline fill="none" stroke="#f59e0b" strokeWidth={1} opacity={.6} points={D.med.filter(m=>m.r>0).map(m=>`${m.dy/8*290+5},${55-m.r/1.3*45}`).join(" ")}/>
            <text x={5} y={10} fill="#1e3a5f" fontSize={6} fontFamily="inherit">Inscribed Radius (HU)</text>
          </svg>
        </div>}

        {tab==="hull"&&<div>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginBottom:8,letterSpacing:1}}>CONVEX HULL</div>
          <Stat label="Solidity" value={D.hull.sol} unit="A/A_hull"/>
          <Stat label="Hull Area" value={D.hull.ha} unit="HU²"/>
          <Stat label="Silhouette Area" value={D.hull.sa} unit="HU²"/>
          <Stat label="Negative Space" value={D.hull.na} unit="HU²" accent="#ef4444"/>
          <div style={{fontSize:10,color:"#3b5068",fontWeight:600,marginTop:14,marginBottom:8,letterSpacing:1}}>VOLUMETRIC ESTIMATES (HU³)</div>
          <Stat label="Cylindrical (π∫dx²dy)" value={D.vol.cyl} accent="#0ea5e9"/>
          <Stat label="Ellipsoidal (π/4∫dx²dy)" value={D.vol.ell} accent="#818cf8"/>
          <Stat label="Pappus (2π∫x·w·dy)" value={D.vol.pap} accent="#f59e0b"/>
          <div style={{marginTop:12,fontSize:8,color:"#172030",lineHeight:1.6}}>
            Cylindrical assumes circular cross-sections from half-width. Ellipsoidal uses π/4 scaling for elliptical sections. Pappus applies the theorem of Pappus for revolution solids using centroid distance. All values in head-unit cubed.
          </div>
        </div>}
      </div>

      <div style={{display:"flex",justifyContent:"center",alignItems:"center",gap:12,marginTop:16}}>
        <div style={{fontSize:7,color:"#0d1520"}}>{fileName} · schema {D.version} · {D.contour.length} pts · {D.strokes.length} strokes · {D.landmarks.length} landmarks</div>
        <button onClick={onReset} style={{background:"transparent",border:"1px solid #172030",color:"#3b5068",padding:"2px 8px",borderRadius:3,fontSize:9,cursor:"pointer",fontFamily:"inherit"}}>Load Another</button>
      </div>
    </div>
  );
}
