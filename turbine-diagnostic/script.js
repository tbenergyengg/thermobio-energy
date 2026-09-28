const MASTER_KEY="tst1025_master_v1", HISTORY_KEY="tst1025_history_v1";
const masterFields=[
["project","Project / Site"],["client","Client / End User"],["turbineModel","Turbine Model"],["turbineType","Turbine Type"],
["ratedPower","Rated Power"],["inletPressureDesign","Design Inlet Pressure"],["inletTempDesign","Design Inlet Temperature"],
["inletFlowDesign","Design Inlet Flow"],["exhaustPressureDesign","Design Exhaust Pressure"],["turbineSpeedDesign","Turbine Speed"],
["alternatorSpeedDesign","Alternator Speed"],["gearboxModel","Gearbox"],["oilGrade","Lubricating Oil Grade"],["oilTankCapacity","Oil Tank Normal Capacity"],["manualRef","Manual / Document Reference"]
];
const groups={Steam:[
["load","Generator Load","kW"],["flow","Inlet Steam Flow","TPH"],["ip","Inlet Steam Pressure","kg/cm²(g)"],["it","Inlet Steam Temperature","°C"],
["wp","Wheel Case Pressure","kg/cm²(g)"],["ep","Exhaust Steam Pressure","kg/cm²(g)"],["et","Exhaust Steam Temperature","°C"],
["ts","Turbine Speed","RPM"],["as","Alternator Speed","RPM"],["tv","Throttle Valve Position","%"],["sdp","Steam Strainer DP","plant unit"]],
Bearing:[
["jt","Journal Bearing Temperature","°C"],["tt","Thrust Bearing Temperature","°C"],["gbt","Gearbox Bearing Temperature","°C"],
["gbb","Generator Bearing Temperature","°C"],["gwt","Generator Winding Temperature","°C"],["vib","Casing Vibration","mm/sec"],
["axn","Axial Displacement Non-active","mils"],["axa","Axial Displacement Active","mils"]],
Oil:[
["lop","Lube Oil Pressure","kg/cm²(g)"],["cop","Control Oil Pressure","kg/cm²(g)"],["top","Trip Oil Pressure","kg/cm²(g)"],
["ob","Lube Oil Temp Before Cooler","°C"],["oa","Lube Oil Temp After Cooler","°C"],["fdp","Lube Oil Filter DP","plant unit"]],
Cooling:[
["ci","Cooling Water Inlet Temperature","°C"],["co","Cooling Water Outlet Temperature","°C"],["cf","Cooling Water Flow","LPM"],
["cp","Cooling Water Pressure","plant unit"],["cdp","Cooling Water DP","plant unit"]]};
const limits={ip:[null,null,47.25,49.5],it:[420,410,470,475],ep:[null,null,4.73,4.95],et:[null,null,260,null],jt:[null,null,105,110],tt:[null,null,110,115],gbt:[null,null,108,115],gbb:[null,null,85,90],gwt:[null,null,150,160],vib:[null,null,12,18],axn:[-17,-21,null,null],axa:[null,null,6,10],lop:[1.4,1.2,null,null],cop:[3.8,3.5,null,null],top:[null,0.8,null,null],ob:[null,null,65,null],oa:[null,null,55,null]};
const names={ip:"Inlet steam pressure",it:"Inlet steam temperature",ep:"Exhaust steam pressure",et:"Exhaust steam temperature",jt:"Journal bearing temperature",tt:"Thrust bearing temperature",gbt:"Gearbox bearing temperature",gbb:"Generator bearing temperature",gwt:"Generator winding temperature",vib:"Casing vibration",axn:"Axial displacement non-active",axa:"Axial displacement active",lop:"Lube oil pressure",cop:"Control oil pressure",top:"Trip oil pressure",ob:"Lube oil temperature before cooler",oa:"Lube oil temperature after cooler"};
const causes={lop:"Check main/auxiliary oil pump, suction, filter, cooler, leakage and oil temperature.",jt:"Check cooling water, oil cooler, oil level, auxiliary pump, alignment/friction and bearing condition.",vib:"Check imbalance, rotor rubbing, alignment, foundation, coupling, pipeline strain and labyrinth clearance.",ep:"Check exhaust-side valves and flow path; high exhaust pressure can reduce turbine power.",et:"Trend exhaust temperature at comparable operating conditions; rising temperature can indicate deposits.",ip:"Verify steam pressure indication, steam condition and control/protection system.",it:"Verify steam temperature indication and steam supply condition.",oa:"Check cooling-water availability, cooler cleanliness, inlet temperature and cooler performance."};
function q(id){return document.getElementById(id)}
function makeFields(){q("masterForm").innerHTML=masterFields.map(x=>`<label>${x[1]}<input id="m_${x[0]}" type="text"></label>`).join("");
let html="";for(const [g,arr] of Object.entries(groups)){html+=`<div class="panel"><h2>${g}</h2><div class="formgrid">`;for(const [id,label,unit] of arr)html+=`<label>${label} (${unit})<input id="${id}" type="number" step="any" inputmode="decimal"></label>`;html+="</div></div>"}q("inspectionGroups").innerHTML=html}
function loadMaster(){try{const d=JSON.parse(localStorage.getItem(MASTER_KEY)||"null");if(!d)return false;masterFields.forEach(([k])=>q("m_"+k).value=d[k]||"");setMasterBadge(true);return true}catch{return false}}
function setMasterBadge(ok){q("masterStatus").textContent=ok?"Master data saved ✓":"Master data not saved";q("masterStatus").className="pill "+(ok?"green":"gray");q("dashMaster").textContent=ok?"Saved ✓":"Not saved"}
function saveMaster(){const d={};masterFields.forEach(([k])=>d[k]=q("m_"+k).value.trim());if(!d.project&&!d.turbineModel){alert("Please enter at least Project/Site and Turbine Model.");return}localStorage.setItem(MASTER_KEY,JSON.stringify(d));setMasterBadge(true);alert("Master data saved. You will not need to fill it again on this browser.")}
function exportMaster(){const d=localStorage.getItem(MASTER_KEY)||JSON.stringify({});download(new Blob([d],{type:"application/json"}),"TST-1025-HB_Master_Data.json")}
function importMaster(e){const f=e.target.files[0];if(!f)return;const r=new FileReader();r.onload=()=>{try{const d=JSON.parse(r.result);localStorage.setItem(MASTER_KEY,JSON.stringify(d));loadMaster()}catch{alert("Invalid master-data file.")}};r.readAsText(f)}
function status(k,v){const [la,lt,ha,ht]=limits[k];if(lt!==null&&v<=lt)return"TRIP";if(ht!==null&&v>=ht)return"TRIP";if(la!==null&&v<=la)return"ALARM";if(ha!==null&&v>=ha)return"ALARM";return"NORMAL"}
function diagnostic(){let res=[],trips=[],alarms=[];for(const k of Object.keys(limits)){const el=q(k);if(!el)continue;const raw=el.value.trim();if(!raw)continue;const v=Number(raw);if(!Number.isFinite(v))continue;const s=status(k,v);res.push({k,v,s});if(s==="TRIP")trips.push(k);if(s==="ALARM")alarms.push(k)}
const overall=trips.length?"TRIP":alarms.length?"ALARM":"NORMAL";q("inspectionStatus").textContent=overall;q("inspectionStatus").className="status big "+overall.toLowerCase();
let html=`<div class="resultbox ${overall.toLowerCase()}"><div class="resulthead"><h2>Diagnostic Result</h2><span class="status ${overall.toLowerCase()}">${overall}</span></div>`;
if(!res.length)html+="<p class='muted'>Enter at least one monitored parameter.</p>";
for(const r of res)html+=`<div class="diagnosis"><b>${names[r.k]}</b> — ${r.v} → <strong>${r.s}</strong></div>`;
const flow=num("flow"),load=num("load"),ip=num("ip"),ep=num("ep");if(flow&&load>0)html+=`<div class="diagnosis"><b>Specific Steam Consumption:</b> ${(flow*1000/load).toFixed(3)} kg/kWh</div>`;
if(flow&&ip!==null&&ep!==null&&flow>0){const p1=ip*.980665+1.01325,p2=ep*.980665+1.01325,d=flow*1000/3600;html+=`<div class="diagnosis"><b>Pressure Characteristic Index C:</b> ${((p1*p1-p2*p2)/(d*d)).toFixed(6)} <span class="muted">(trend indicator)</span></div>`}
const affected=[...new Set([...trips,...alarms])];if(affected.length){html+="<div class='diagnosis'><b>Recommended checks</b>";affected.forEach(k=>html+=`<p class="muted"><b>${names[k]}:</b> ${causes[k]||"Check the corresponding instrument, process condition and protection system."}</p>`);html+="</div>"}html+="</div>";q("result").innerHTML=html;
return {overall,res}}
function num(id){const e=q(id);if(!e||e.value==="")return null;const n=Number(e.value);return Number.isFinite(n)?n:null}
function saveInspection(){const d={time:new Date().toISOString(),status:diagnostic().overall};for(const [g,a] of Object.entries(groups))a.forEach(([id])=>d[id]=q(id).value);d.remarks=q("remarks").value;d.alarmTrip=q("alarmTrip").value;d.noise=q("noise").value;let h=JSON.parse(localStorage.getItem(HISTORY_KEY)||"[]");h.unshift(d);h=h.slice(0,500);localStorage.setItem(HISTORY_KEY,JSON.stringify(h));renderHistory();q("dashResult").textContent=d.status;q("dashCount").textContent=h.length}
function renderHistory(){const h=JSON.parse(localStorage.getItem(HISTORY_KEY)||"[]");q("dashCount").textContent=h.length;if(!h.length){q("historyBody").innerHTML="<tr><td colspan='8' class='empty'>No saved inspections yet.</td></tr>";return}q("historyBody").innerHTML=h.map(x=>`<tr><td>${new Date(x.time).toLocaleString()}</td><td><strong>${x.status}</strong></td><td>${x.load||"—"}</td><td>${x.flow||"—"}</td><td>${x.ip||"—"}</td><td>${x.it||"—"}</td><td>${x.vib||"—"}</td><td>${x.remarks||"—"}</td></tr>`).join("")}
function exportCSV(){const h=JSON.parse(localStorage.getItem(HISTORY_KEY)||"[]");if(!h.length){alert("No inspection history to export.");return}const keys=[...new Set(h.flatMap(Object.keys))];const csv=[keys.join(","),...h.map(r=>keys.map(k=>`"${String(r[k]??"").replaceAll('"','""')}"`).join(","))].join("\n");download(new Blob([csv],{type:"text/csv"}),"turbine_inspection_history.csv")}
function download(blob,name){const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500)}
function showSection(id){document.querySelectorAll(".section").forEach(s=>s.classList.toggle("active",s.id===id));document.querySelectorAll(".nav").forEach(n=>n.classList.toggle("active",n.dataset.section===id));window.scrollTo({top:0,behavior:"smooth"})}
document.querySelectorAll(".nav").forEach(n=>n.addEventListener("click",()=>showSection(n.dataset.section)));
q("saveMaster").addEventListener("click",saveMaster);q("exportMaster").addEventListener("click",exportMaster);q("importMaster").addEventListener("change",importMaster);
q("inspectionForm").addEventListener("submit",e=>{e.preventDefault();saveInspection()});q("clearInspection").addEventListener("click",()=>{q("inspectionForm").reset();q("result").innerHTML="";q("inspectionStatus").textContent="READY";q("inspectionStatus").className="status big neutral";q("date")&&(q("date").value="")});
q("exportCSV").addEventListener("click",exportCSV);makeFields();const saved=loadMaster();setMasterBadge(saved);renderHistory();const hh=JSON.parse(localStorage.getItem(HISTORY_KEY)||"[]");if(hh[0])q("dashResult").textContent=hh[0].status;
