
import os, json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from jose import jwt, JWTError
from pydantic import BaseModel
from metrics_report import summary_metrics, equity_curve
from health_monitor import health_check_endpoint
from tax_tracker import TaxTracker

SECRET = os.getenv("DASHBOARD_JWT_SECRET","change_me")
ALGO="HS256"; TTL=int(os.getenv("DASHBOARD_TOKEN_TTL_MIN","720"))
USER=os.getenv("DASHBOARD_USER","admin"); PASS=os.getenv("DASHBOARD_PASS","password")
app=FastAPI(title="Crypto Bot Dashboard"); bearer=HTTPBearer()

def create_token(sub): 
    exp=datetime.now(timezone.utc)+timedelta(minutes=TTL)
    return jwt.encode({"sub":sub,"exp":exp}, SECRET, algorithm=ALGO)
def require_auth(token: HTTPAuthorizationCredentials = Depends(bearer)):
    try: return jwt.decode(token.credentials, SECRET, algorithms=[ALGO])["sub"]
    except JWTError: raise HTTPException(status_code=401, detail="Invalid token")

class LoginForm(BaseModel): username: str; password: str

@app.post("/api/login")
async def login(f: LoginForm): 
    if f.username!=USER or f.password!=PASS: raise HTTPException(status_code=401, detail="Bad credentials")
    return {"access_token": create_token(f.username), "token_type":"bearer", "expires_min":TTL}

@app.get("/api/status")
async def status(user: str=Depends(require_auth)):
    p=Path("risk_state.json"); state={}
    if p.exists():
        try: state=json.loads(p.read_text())
        except Exception: state={}
    return {"user":user, "time":datetime.now(timezone.utc).isoformat(), "state":state}

@app.get("/api/positions")
async def positions(user: str=Depends(require_auth)):
    p=Path("risk_state.json"); pos={}
    if p.exists():
        try: pos=json.loads(p.read_text()).get("open_positions",{})
        except Exception: pos={}
    return pos

@app.get("/api/metrics")
async def metrics(user: str=Depends(require_auth)):
    try: m=summary_metrics("trade_history.csv")
    except Exception: m={}
    return m

@app.get("/api/equity")
async def equity(user: str=Depends(require_auth)):
    try: eq=equity_curve("trade_history.csv")
    except Exception: eq=[]
    return eq


@app.get("/healthz")
async def healthz():
    return {"ok": True, "ts": datetime.now(timezone.utc).isoformat()}

@app.get("/api/trades")
async def trades(user: str=Depends(require_auth)):
    fp=Path("trade_history.csv")
    if not fp.exists(): return []
    rows=fp.read_text().splitlines()
    head=rows[0].split(","); data=[dict(zip(head,r.split(","))) for r in rows[1:]]
    return data[-200:]

@app.get("/api/health")
async def health(user: str=Depends(require_auth)):
    try: return health_check_endpoint()
    except Exception as e: return {"error": str(e)}

@app.get("/api/tax/summary")
async def tax_summary(user: str=Depends(require_auth)):
    try: 
        tracker = TaxTracker()
        summary = tracker.get_portfolio_summary()
        tracker.close()
        return summary
    except Exception as e: return {"error": str(e)}

@app.get("/api/tax/1099b/{year}")
async def tax_1099b(year: int, user: str=Depends(require_auth)):
    try:
        tracker = TaxTracker()
        data = tracker.generate_1099_b_data(year)
        tracker.close()
        return data
    except Exception as e: return {"error": str(e)}

INDEX = """
<!doctype html><html><head><meta charset="UTF-8"><title>Bot Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>body{font-family:Arial;margin:20px}.card{border:1px solid #ccc;padding:12px;border-radius:8px;margin:12px 0}</style>
</head><body>
<h2>Crypto Bot Dashboard</h2>
<div id="login" class="card">
  <b>Login</b><br/>
  <input id="u" placeholder="username"> <input id="p" type="password" placeholder="password">
  <button onclick="login()">Login</button> <span id="msg" style="color:red"></span>
</div>
<div id="content" style="display:none;">
  <div class="card"><b>System Health</b><pre id="health"></pre></div>
  <div class="card"><b>Equity Curve</b><canvas id="eq" height="120"></canvas></div>
  <div class="card"><b>Trading Metrics</b><pre id="metrics"></pre></div>
  <div class="card"><b>Bot Status</b><pre id="status"></pre></div>
  <div class="card"><b>Open Positions</b><pre id="positions"></pre></div>
  <div class="card"><b>Tax Summary</b><pre id="taxSummary"></pre></div>
  <div class="card"><b>Recent Trades</b><pre id="trades"></pre></div>
</div>
<script>
let token=null;
async function login(){
  const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:document.getElementById('u').value,password:document.getElementById('p').value})});
  if(!r.ok){document.getElementById('msg').innerText='Login failed';return;}
  token=(await r.json()).access_token; document.getElementById('login').style.display='none'; document.getElementById('content').style.display='block';
  poll(); setInterval(poll, 10000);
}
async function poll(){
  async function g(u){return (await fetch(u,{headers:{'Authorization':'Bearer '+token}})).json()}
  const s=await g('/api/status'); const p=await g('/api/positions'); const m=await g('/api/metrics'); 
  const eq=await g('/api/equity'); const t=await g('/api/trades'); const h=await g('/api/health');
  const tax=await g('/api/tax/summary');
  
  document.getElementById('status').innerText=JSON.stringify(s,null,2);
  document.getElementById('positions').innerText=JSON.stringify(p,null,2);
  document.getElementById('metrics').innerText=JSON.stringify(m,null,2);
  document.getElementById('trades').innerText=JSON.stringify(t.slice(-10),null,2);
  document.getElementById('health').innerText=JSON.stringify(h,null,2);
  document.getElementById('taxSummary').innerText=JSON.stringify(tax,null,2);
  try{
    const ctx=document.getElementById('eq').getContext('2d');
    const labels=eq.map(x=>x.t); const data=eq.map(x=>x.equity);
    if(!window.eqChart){ window.eqChart=new Chart(ctx,{type:'line',data:{labels,datasets:[{label:'Equity',data}]},options:{animation:false,responsive:true,scales:{x:{display:false}}}}); }
    else{ window.eqChart.data.labels=labels; window.eqChart.data.datasets[0].data=data; window.eqChart.update(); }
  }catch(e){}
}
</script></body></html>
"""
@app.get("/", response_class=HTMLResponse)
async def index(): return HTMLResponse(INDEX)
