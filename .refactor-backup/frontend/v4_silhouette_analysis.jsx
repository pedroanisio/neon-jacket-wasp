import { useState, useMemo, useCallback } from "react";

const D = {"c":[[.007,.005],[.032,.006],[.069,.008],[.105,.013],[.141,.021],[.177,.03],[.212,.042],[.246,.056],[.279,.071],[.311,.089],[.342,.11],[.371,.132],[.398,.157],[.423,.183],[.446,.212],[.467,.243],[.484,.275],[.5,.308],[.512,.343],[.523,.378],[.532,.413],[.538,.45],[.542,.486],[.545,.523],[.547,.56],[.55,.596],[.55,.633],[.547,.67],[.545,.706],[.542,.743],[.538,.779],[.532,.816],[.525,.852],[.517,.888],[.508,.923],[.499,.959],[.489,.995],[.478,1.03],[.467,1.065],[.453,1.099],[.434,1.129],[.409,1.157],[.382,1.181],[.353,1.204],[.328,1.229],[.317,1.26],[.325,1.292],[.345,1.323],[.371,1.348],[.402,1.367],[.436,1.381],[.47,1.393],[.505,1.405],[.541,1.415],[.576,1.424],[.612,1.433],[.648,1.441],[.684,1.448],[.72,1.456],[.755,1.465],[.789,1.479],[.822,1.496],[.853,1.516],[.882,1.538],[.908,1.564],[.931,1.593],[.949,1.625],[.963,1.659],[.974,1.694],[.983,1.729],[.99,1.765],[.995,1.802],[.997,1.838],[.998,1.875],[.998,1.912],[.998,1.949],[.998,1.986],[.999,2.022],[1.003,2.059],[1.01,2.095],[1.018,2.131],[1.027,2.166],[1.035,2.202],[1.043,2.238],[1.049,2.274],[1.055,2.311],[1.059,2.347],[1.063,2.384],[1.067,2.421],[1.071,2.457],[1.08,2.492],[1.095,2.525],[1.111,2.558],[1.124,2.591],[1.139,2.624],[1.156,2.656],[1.168,2.69],[1.177,2.726],[1.185,2.762],[1.193,2.798],[1.2,2.834],[1.203,2.87],[1.199,2.906],[1.192,2.942],[1.19,2.978],[1.194,3.014],[1.199,3.051],[1.203,3.087],[1.207,3.124],[1.211,3.16],[1.215,3.197],[1.219,3.233],[1.223,3.27],[1.227,3.307],[1.232,3.343],[1.237,3.38],[1.242,3.416],[1.249,3.452],[1.261,3.486],[1.274,3.521],[1.281,3.556],[1.283,3.593],[1.283,3.63],[1.283,3.666],[1.283,3.703],[1.28,3.74],[1.275,3.776],[1.273,3.812],[1.278,3.848],[1.284,3.884],[1.291,3.921],[1.298,3.957],[1.304,3.993],[1.308,4.029],[1.303,4.065],[1.29,4.099],[1.272,4.131],[1.256,4.164],[1.24,4.197],[1.225,4.231],[1.205,4.261],[1.178,4.284],[1.146,4.303],[1.113,4.32],[1.081,4.337],[1.05,4.356],[1.018,4.375],[.984,4.386],[.955,4.379],[.941,4.353],[.945,4.319],[.952,4.284],[.944,4.253],[.929,4.221],[.92,4.187],[.92,4.15],[.92,4.114],[.919,4.077],[.917,4.04],[.913,4.003],[.91,3.967],[.91,3.93],[.915,3.894],[.924,3.858],[.934,3.823],[.939,3.788],[.934,3.753],[.923,3.718],[.914,3.682],[.905,3.647],[.896,3.611],[.89,3.575],[.892,3.539],[.897,3.503],[.897,3.467],[.89,3.431],[.88,3.395],[.869,3.36],[.856,3.326],[.843,3.292],[.83,3.257],[.816,3.223],[.802,3.189],[.789,3.155],[.778,3.119],[.769,3.084],[.762,3.048],[.757,3.011],[.753,2.975],[.751,2.938],[.747,2.902],[.739,2.866],[.732,2.83],[.725,2.795],[.716,2.759],[.709,2.723],[.705,2.687],[.698,2.651],[.687,2.615],[.674,2.581],[.661,2.547],[.641,2.518],[.613,2.504],[.584,2.513],[.565,2.541],[.556,2.576],[.55,2.612],[.545,2.648],[.541,2.685],[.538,2.722],[.539,2.758],[.543,2.795],[.55,2.831],[.56,2.866],[.573,2.901],[.586,2.935],[.599,2.97],[.607,3.005],[.603,3.038],[.591,3.071],[.589,3.104],[.604,3.135],[.627,3.163],[.646,3.194],[.659,3.228],[.672,3.263],[.682,3.297],[.688,3.333],[.694,3.369],[.704,3.404],[.717,3.439],[.73,3.473],[.742,3.508],[.752,3.543],[.762,3.579],[.771,3.615],[.78,3.65],[.787,3.686],[.795,3.722],[.802,3.758],[.809,3.795],[.815,3.831],[.82,3.867],[.825,3.904],[.829,3.94],[.833,3.977],[.835,4.014],[.836,4.05],[.836,4.087],[.836,4.124],[.836,4.161],[.835,4.197],[.832,4.234],[.829,4.271],[.826,4.307],[.822,4.344],[.818,4.381],[.814,4.417],[.809,4.454],[.804,4.49],[.799,4.527],[.795,4.563],[.79,4.6],[.785,4.636],[.78,4.673],[.775,4.709],[.771,4.746],[.766,4.782],[.761,4.819],[.757,4.855],[.752,4.892],[.748,4.928],[.744,4.965],[.74,5.001],[.736,5.038],[.732,5.074],[.728,5.111],[.726,5.148],[.725,5.184],[.726,5.221],[.725,5.258],[.724,5.295],[.722,5.331],[.724,5.367],[.729,5.404],[.73,5.44],[.727,5.476],[.728,5.513],[.733,5.549],[.739,5.586],[.743,5.622],[.748,5.659],[.754,5.695],[.76,5.731],[.766,5.768],[.772,5.804],[.778,5.84],[.783,5.877],[.788,5.913],[.791,5.95],[.794,5.986],[.796,6.023],[.797,6.06],[.797,6.097],[.797,6.133],[.796,6.17],[.794,6.207],[.79,6.244],[.787,6.28],[.783,6.317],[.778,6.353],[.774,6.39],[.769,6.426],[.765,6.463],[.76,6.499],[.756,6.536],[.753,6.573],[.751,6.609],[.748,6.646],[.746,6.683],[.744,6.719],[.741,6.756],[.739,6.793],[.743,6.829],[.75,6.864],[.752,6.9],[.744,6.935],[.738,6.97],[.74,7.006],[.75,7.04],[.769,7.07],[.79,7.099],[.801,7.132],[.802,7.168],[.8,7.205],[.797,7.242],[.795,7.278],[.786,7.313],[.778,7.347],[.781,7.381],[.793,7.416],[.798,7.451],[.796,7.487],[.795,7.523],[.803,7.558],[.818,7.592],[.834,7.625],[.851,7.657],[.869,7.689],[.89,7.72],[.912,7.749],[.935,7.777],[.957,7.807],[.975,7.839],[.987,7.873],[.99,7.909],[.984,7.944],[.964,7.971],[.932,7.986],[.896,7.992],[.86,7.994],[.823,7.997],[.786,7.999],[.75,8],[.75,8]],"l":[{"n":"crown","d":"Top of head/helmet","dy":.005,"dx":.0066},{"n":"head_peak","d":"Widest point of head/helmet","dy":.6146,"dx":.5634},{"n":"chin","d":"Jaw/chin narrowing","dy":1.2438,"dx":.3203},{"n":"neck_valley","d":"Narrowest head-shoulder","dy":1.2595,"dx":.3302},{"n":"trapezius_peak","d":"Neck-shoulder transition","dy":2.2022,"dx":1.035},{"n":"shoulder_peak","d":"Widest at shoulders","dy":2.2926,"dx":1.0651},{"n":"chest_inflection","d":"Chest plate contour","dy":2.5468,"dx":.6609},{"n":"armpit_valley","d":"Arm junction narrowing","dy":2.5981,"dx":.6809},{"n":"waist_valley","d":"Narrowest torso","dy":2.7034,"dx":.5523},{"n":"navel_estimate","d":"Estimated navel position","dy":3.2911,"dx":.9007},{"n":"hip_peak","d":"Widest at hips","dy":3.9567,"dx":1.311},{"n":"mid_thigh","d":"Mid thigh","dy":4.6166,"dx":.7876},{"n":"thigh_narrowing","d":"Lower thigh armor edge","dy":4.8003,"dx":.7635},{"n":"knee_valley","d":"Narrowest at knee","dy":5.2765,"dx":.6007},{"n":"calf_peak","d":"Widest calf","dy":6.0967,"dx":.7967},{"n":"mid_shin","d":"Mid shin","dy":6.1324,"dx":.7968},{"n":"ankle_valley","d":"Narrowest at ankle","dy":6.9882,"dx":.7376},{"n":"boot_top","d":"Boot widest","dy":7.9093,"dx":.9903},{"n":"sole","d":"Bottom of boot","dy":8.0001,"dx":.7497}],"wp":[{"dy":.015,"w":.228},{"dy":.115,"w":.699},{"dy":.215,"w":.896},{"dy":.315,"w":1.005},{"dy":.415,"w":1.064},{"dy":.515,"w":1.089},{"dy":.615,"w":1.101},{"dy":.715,"w":1.089},{"dy":.815,"w":1.064},{"dy":.915,"w":1.021},{"dy":1.015,"w":.966},{"dy":1.115,"w":.888},{"dy":1.215,"w":.681},{"dy":1.315,"w":.678},{"dy":1.415,"w":1.08},{"dy":1.515,"w":1.703},{"dy":1.615,"w":1.888},{"dy":1.715,"w":1.96},{"dy":1.815,"w":1.992},{"dy":1.915,"w":1.995},{"dy":2.015,"w":1.996},{"dy":2.115,"w":2.03},{"dy":2.215,"w":2.076},{"dy":2.315,"w":2.111},{"dy":2.415,"w":2.134},{"dy":2.615,"w":1.299},{"dy":2.715,"w":1.61},{"dy":2.815,"w":1.78},{"dy":4.415,"w":1.6},{"dy":4.515,"w":1.602},{"dy":4.615,"w":1.576},{"dy":4.715,"w":1.549},{"dy":4.815,"w":1.523},{"dy":4.915,"w":1.498},{"dy":5.015,"w":1.478},{"dy":5.115,"w":1.455},{"dy":5.215,"w":1.451},{"dy":5.315,"w":1.444},{"dy":5.415,"w":1.459},{"dy":5.515,"w":1.456},{"dy":5.615,"w":1.485},{"dy":5.715,"w":1.515},{"dy":5.815,"w":1.548},{"dy":5.915,"w":1.576},{"dy":6.015,"w":1.592},{"dy":6.115,"w":1.594},{"dy":6.215,"w":1.586},{"dy":6.315,"w":1.566},{"dy":6.415,"w":1.542},{"dy":6.515,"w":1.517},{"dy":6.615,"w":1.5},{"dy":6.715,"w":1.488},{"dy":6.815,"w":1.482},{"dy":6.915,"w":1.498},{"dy":7.015,"w":1.482},{"dy":7.115,"w":1.595},{"dy":7.215,"w":1.598},{"dy":7.315,"w":1.571},{"dy":7.415,"w":1.585},{"dy":7.515,"w":1.589},{"dy":7.615,"w":1.658},{"dy":7.715,"w":1.773},{"dy":7.815,"w":1.923},{"dy":7.915,"w":1.98}],"ar":[{"n":"cranium","h":.61,"a":.492,"f":.0397,"mw":.875},{"n":"face","h":.645,"a":.593,"f":.0479,"mw":.982},{"n":"neck","h":.671,"a":1.032,"f":.0833,"mw":1.569},{"n":"shoulders","h":.512,"a":.928,"f":.0749,"mw":2.062},{"n":"upper_torso","h":.261,"a":.266,"f":.0215,"mw":1.374},{"n":"lower_torso","h":1.253,"a":2.159,"f":.1742,"mw":1.817},{"n":"upper_leg","h":1.32,"a":2.202,"f":.1777,"mw":1.683},{"n":"lower_leg","h":1.712,"a":2.512,"f":.2027,"mw":1.521},{"n":"foot","h":1.012,"a":1.6,"f":.1291,"mw":1.686}],"sd":{"canon":"loomis_8_head_academic","fh":6.373,"ch":8,"l2":.212,"pos":[{"n":"crown","m":0,"c":0,"d":0},{"n":"chin","m":.1549,"c":.125,"d":.0299},{"n":"navel_estimate","m":.411,"c":.375,"d":.036},{"n":"mid_thigh","m":.5768,"c":.625,"d":-.0482},{"n":"knee_valley","m":.6593,"c":.75,"d":-.0907},{"n":"mid_shin","m":.7664,"c":.875,"d":-.1086},{"n":"sole","m":1,"c":1,"d":0}],"wid":[{"n":"head_width","m":.1409,"c":.125,"d":.0159},{"n":"shoulder_width","m":.2664,"c":.25,"d":.0164},{"n":"waist_width","m":.1382,"c":.15,"d":-.0118},{"n":"hip_width","m":.328,"c":.1875,"d":.1405}]},"sc":{"curvature_entropy":{"value":3.3041,"units":"bits"},"fractal_dimension":{"value":.9585},"compactness":{"value":.2226},"rectangularity":{"value":1.1738},"eccentricity":{"value":.9127},"roughness":{"value":1.4104}},"gl":{"lean":3.31,"li":"slight_lean_right","cp":.0129,"ci":"subtle","en":.2548,"ctr_dx":.718,"ctr_dy":3.818},"pr":{"hc":6.373,"sr":{"crown→head_peak":.087295,"head_peak→neck_valley":.09235,"neck_valley→shoulder_peak":.147941,"shoulder_peak→waist_valley":.058827,"waist_valley→hip_peak":.179474,"hip_peak→knee_valley":.188996,"knee_valley→ankle_valley":.245117},"comp":{"torso_to_leg":.4116,"upper_to_lower_body":.9773,"shoulder_to_hip_width":.8124,"waist_to_hip_width":.4213,"leg_fraction":.5054},"canons":[{"sys":"Loomis 8-head","heads":8},{"sys":"Heroic 8.5-head","heads":8.5}]},"vol":{"cyl":18.423,"ell":9.212,"pap":36.847},"hull":{"sol":.7354,"ha":16.855,"sa":12.395,"na":4.46},"br":[{"n":"cranium","s":.005,"e":.615},{"n":"face","s":.615,"e":1.26},{"n":"neck","s":1.26,"e":1.931},{"n":"shoulders","s":1.931,"e":2.443},{"n":"upper_torso","s":2.443,"e":2.703},{"n":"lower_torso","s":2.703,"e":3.957},{"n":"upper_leg","s":3.957,"e":5.277},{"n":"lower_leg","s":5.277,"e":6.988},{"n":"foot","s":6.988,"e":8}],"bio":{"hcm":170,"sc":21.26,"com_dy":3.7417,"com_frac":.4674},"med":[{"dy":.015,"r":.114},{"dy":.215,"r":.448},{"dy":.415,"r":.532},{"dy":.615,"r":.55},{"dy":.815,"r":.532},{"dy":1.015,"r":.483},{"dy":1.215,"r":.341},{"dy":1.415,"r":.54},{"dy":1.615,"r":.944},{"dy":1.815,"r":.996},{"dy":2.015,"r":.998},{"dy":2.215,"r":1.038},{"dy":2.415,"r":1.067},{"dy":2.615,"r":.649},{"dy":2.815,"r":.89},{"dy":3.015,"r":1.248},{"dy":3.215,"r":1.199},{"dy":3.415,"r":1.163},{"dy":3.615,"r":.693},{"dy":4.015,"r":.652},{"dy":4.215,"r":.999},{"dy":4.415,"r":.8},{"dy":4.615,"r":.788},{"dy":4.815,"r":.762},{"dy":5.015,"r":.739},{"dy":5.215,"r":.726},{"dy":5.415,"r":.73},{"dy":5.615,"r":.742},{"dy":5.815,"r":.774},{"dy":6.015,"r":.796},{"dy":6.215,"r":.793},{"dy":6.415,"r":.771},{"dy":6.615,"r":.75},{"dy":6.815,"r":.741},{"dy":7.015,"r":.741},{"dy":7.215,"r":.799},{"dy":7.415,"r":.792},{"dy":7.615,"r":.829},{"dy":7.815,"r":.962}]};

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
          <span style={{fontSize:9,color:"#1e3a5f",letterSpacing:.6}}>v4.0 · FRONT · ARMORED · FEMALE · {D.pr.hc.toFixed(1)} HU</span>
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

      <div style={{fontSize:7,color:"#0d1520",marginTop:16,textAlign:"center"}}>
        schema v4.0 · floodfill · score 0.896 · 1200 pts · 50 strokes · 19 landmarks
      </div>
    </div>
  );
}
