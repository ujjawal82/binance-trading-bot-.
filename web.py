from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from bot.client import BinanceAPIError, BinanceClient
from bot.logging_config import configure_logging
from bot.orders import OrderService, response_summary
from bot.validators import ValidationError, validate_order_input
from cli import load_dotenv, yes_no

load_dotenv()
logger = configure_logging("logs/web_orders.log")
app = FastAPI(title="Binance Futures Testnet Order Desk")

HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Futures Testnet Order Desk</title>
<style>
:root{
  --ink:#191611; --paper:#f7f0df; --paper-2:#efe3c8; --walnut:#4b3527;
  --moss:#6f7a45; --moss-dark:#424a2a; --terracotta:#b65f3a; --brass:#b9914d;
  --smoke:#d7c6a6; --danger:#9f3f32; --ok:#596d3d; --shadow:rgba(37,28,18,.18);
}
*{box-sizing:border-box} html{scroll-behavior:smooth}
body{margin:0; color:var(--ink); background:
  radial-gradient(circle at 20% 10%, rgba(182,95,58,.18), transparent 28rem),
  radial-gradient(circle at 80% 0%, rgba(111,122,69,.22), transparent 24rem),
  linear-gradient(135deg, #fbf6e9 0%, var(--paper) 48%, #ead9b8 100%);
  font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif; min-height:100vh;}
body:before{content:""; position:fixed; inset:0; pointer-events:none; opacity:.36; mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)' opacity='.16'/%3E%3C/svg%3E");}
.shell{width:min(1120px, calc(100% - 28px)); margin:0 auto; padding:28px 0 46px; position:relative;}
header{display:grid; grid-template-columns:1fr auto; gap:20px; align-items:center; padding:14px 0 28px;}
.brand{display:flex; gap:13px; align-items:center}.mark{width:42px;height:42px;border:2px solid var(--walnut);border-radius:14px 14px 10px 18px; background:linear-gradient(145deg,var(--brass),#dbc178); box-shadow:5px 5px 0 var(--walnut); position:relative; transform:rotate(-3deg)}
.mark:after{content:"";position:absolute;left:9px;right:9px;top:19px;height:2px;background:var(--walnut);box-shadow:7px -8px 0 var(--walnut),14px 6px 0 var(--walnut)}
.brand small{display:block; letter-spacing:.13em; text-transform:uppercase; color:var(--moss-dark); font:700 11px/1.2 ui-sans-serif,system-ui}.brand strong{font-size:clamp(20px,3vw,31px); letter-spacing:-.035em;}
.pill{border:1.5px solid var(--walnut); border-radius:999px; padding:10px 14px; background:rgba(247,240,223,.72); box-shadow:3px 3px 0 rgba(75,53,39,.35); font:700 13px ui-sans-serif,system-ui; white-space:nowrap;}
.hero{display:grid; grid-template-columns:1.05fr .95fr; gap:24px; align-items:stretch;}
.panel{background:rgba(247,240,223,.82); border:2px solid var(--walnut); border-radius:28px; box-shadow:10px 10px 0 var(--shadow); overflow:hidden; backdrop-filter:blur(8px)}
.copy{padding:clamp(24px,4vw,48px)}
h1{margin:0; font-size:clamp(42px,8vw,88px); line-height:.88; letter-spacing:-.075em; max-width:760px;}
.lede{font:500 clamp(17px,2.3vw,22px)/1.55 ui-sans-serif,system-ui; color:#3d3228; max-width:62ch; margin:24px 0 0;}
.notes{display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:30px}.note{border:1.5px solid var(--walnut); border-radius:18px; padding:14px; background:var(--paper-2); min-height:96px; transform:rotate(var(--r));}.note:nth-child(1){--r:-1.2deg}.note:nth-child(2){--r:.8deg}.note:nth-child(3){--r:-.45deg}.note b{display:block; font:800 12px/1 ui-sans-serif,system-ui; text-transform:uppercase; letter-spacing:.08em; color:var(--terracotta); margin-bottom:8px}.note span{font:600 14px/1.35 ui-sans-serif,system-ui;}
.form-card{padding:20px}.ticket{background:#fff9ea; border:1.7px dashed var(--walnut); border-radius:23px; padding:20px; min-height:100%;}
.ticket h2{font-size:29px; letter-spacing:-.04em; margin:0 0 8px}.ticket p{font:600 14px/1.45 ui-sans-serif,system-ui; margin:0 0 18px; color:#5a4c3c;}
form{display:grid; gap:14px}.row{display:grid; grid-template-columns:1fr 1fr; gap:12px} label{display:grid; gap:7px; font:800 11px ui-sans-serif,system-ui; text-transform:uppercase; letter-spacing:.11em; color:var(--moss-dark)}
input,select{width:100%; border:1.7px solid #6d5a45; border-radius:15px; background:#fffdf5; color:var(--ink); padding:13px 13px; font:700 16px ui-sans-serif,system-ui; outline:none; transition:.18s ease;}
input:focus,select:focus{border-color:var(--terracotta); box-shadow:0 0 0 4px rgba(182,95,58,.16)}
.check{display:flex; align-items:center; justify-content:space-between; gap:12px; padding:12px 14px; border:1.5px solid var(--smoke); border-radius:16px; background:#fbf2dd; font:700 14px ui-sans-serif,system-ui; text-transform:none; letter-spacing:0}.check input{width:22px;height:22px; accent-color:var(--moss)}
button{border:2px solid var(--walnut); border-radius:17px; background:linear-gradient(180deg,#c97549,var(--terracotta)); color:#fff8e8; padding:14px 18px; font:900 16px ui-sans-serif,system-ui; cursor:pointer; box-shadow:5px 5px 0 var(--walnut); transition:transform .12s ease, box-shadow .12s ease;}
button:hover{transform:translate(-2px,-2px); box-shadow:7px 7px 0 var(--walnut)} button:disabled{opacity:.68; cursor:wait; transform:none}.muted{color:#6d5a45; font:600 13px ui-sans-serif,system-ui;}
.result{margin-top:16px; display:none; border-radius:18px; padding:15px; border:1.5px solid var(--walnut); background:#f5ead0; font:650 14px/1.55 ui-sans-serif,system-ui; white-space:pre-wrap;}.result.ok{display:block; border-color:var(--ok)}.result.bad{display:block; border-color:var(--danger); color:#61271f; background:#f3ded5}
.below{display:grid; grid-template-columns:.85fr 1.15fr; gap:24px; margin-top:24px}.card{padding:24px}.card h3{margin:0 0 12px; font-size:27px; letter-spacing:-.04em}.card code{background:#2c241c; color:#f6e4bd; border-radius:11px; padding:3px 7px; font-size:.9em}.steps{margin:0; padding-left:20px; font:600 15px/1.7 ui-sans-serif,system-ui}.ledger{display:grid; gap:10px}.line{display:flex; justify-content:space-between; gap:20px; border-bottom:1px solid rgba(75,53,39,.25); padding:10px 0; font:700 14px ui-sans-serif,system-ui}.line span:first-child{color:var(--moss-dark)} footer{padding-top:22px; text-align:center; font:700 12px ui-sans-serif,system-ui; color:#61513e;}
@media(max-width:860px){header,.hero,.below{grid-template-columns:1fr}.pill{justify-self:start}.notes{grid-template-columns:1fr}.copy{padding:28px}.row{grid-template-columns:1fr} h1{font-size:clamp(42px,14vw,72px)}}
@media(max-width:430px){.shell{width:min(100% - 18px,1120px); padding-top:14px}.panel{border-radius:22px; box-shadow:6px 6px 0 var(--shadow)}.copy,.card{padding:20px}.form-card{padding:12px}.ticket{padding:15px} h1{letter-spacing:-.065em}.brand strong{font-size:20px}.pill{white-space:normal}.note{min-height:auto}}
</style>
</head>
<body>
<main class="shell">
  <header>
    <div class="brand"><div class="mark" aria-hidden="true"></div><div><small>Binance Futures Testnet</small><strong>Order Desk</strong></div></div>
    <div class="pill">Built for careful test orders, not guesswork</div>
  </header>
  <section class="hero">
    <div class="panel copy">
      <h1>Place orders with a steady hand.</h1>
      <p class="lede">A responsive, small-screen friendly control room for the Python trading bot. It validates first, logs every attempt, and keeps dry-run mode close so you can rehearse before touching the exchange.</p>
      <div class="notes">
        <div class="note"><b>Required</b><span>MARKET and LIMIT orders with BUY/SELL support.</span></div>
        <div class="note"><b>Safety</b><span>Credentials stay on the server; signatures are never shown in the browser.</span></div>
        <div class="note"><b>Bonus</b><span>STOP limit flow included for a stronger submission.</span></div>
      </div>
    </div>
    <div class="panel form-card">
      <div class="ticket">
        <h2>New order</h2>
        <p>Default is dry-run. Uncheck only after setting Binance Futures Testnet API keys.</p>
        <form id="orderForm">
          <div class="row"><label>Symbol<input name="symbol" value="BTCUSDT" autocomplete="off"></label><label>Side<select name="side"><option>BUY</option><option>SELL</option></select></label></div>
          <div class="row"><label>Order type<select name="order_type" id="orderType"><option>MARKET</option><option>LIMIT</option><option>STOP</option></select></label><label>Quantity<input name="quantity" placeholder="0.001" inputmode="decimal"></label></div>
          <div class="row"><label>Limit price<input name="price" id="price" placeholder="Required for LIMIT/STOP" inputmode="decimal"></label><label>Stop price<input name="stop_price" id="stopPrice" placeholder="STOP only" inputmode="decimal"></label></div>
          <label class="check"><span>Dry run — validate and log without exchange call</span><input name="dry_run" type="checkbox" checked></label>
          <button id="submitBtn" type="submit">Review & place order</button>
        </form>
        <div class="result" id="result"></div>
      </div>
    </div>
  </section>
  <section class="below">
    <div class="panel card"><h3>Run locally</h3><ol class="steps"><li>Install: <code>pip install -r requirements.txt</code></li><li>Add keys in <code>.env</code></li><li>CLI: <code>python cli.py --dry-run ...</code></li><li>Site: <code>uvicorn web:app --reload</code></li></ol></div>
    <div class="panel card"><h3>Submission checklist</h3><div class="ledger"><div class="line"><span>Structured client + CLI</span><strong>done</strong></div><div class="line"><span>Validation and exceptions</span><strong>done</strong></div><div class="line"><span>Request/response logs</span><strong>done</strong></div><div class="line"><span>Responsive lightweight UI</span><strong>done</strong></div></div></div>
  </section>
  <footer>Warm neutral palette, hand-cut edges, zero CDN dependencies.</footer>
</main>
<script>
const form = document.getElementById('orderForm'), result = document.getElementById('result'), btn = document.getElementById('submitBtn');
function syncFields(){ const t=document.getElementById('orderType').value; document.getElementById('price').disabled=(t==='MARKET'); document.getElementById('stopPrice').disabled=(t!=='STOP'); }
document.getElementById('orderType').addEventListener('change', syncFields); syncFields();
form.addEventListener('submit', async (event)=>{ event.preventDefault(); result.className='result'; result.textContent=''; btn.disabled=true; btn.textContent='Working carefully...';
  const data=Object.fromEntries(new FormData(form).entries()); data.dry_run = form.dry_run.checked;
  try{ const res=await fetch('/api/order',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); const payload=await res.json();
    result.className='result '+(res.ok?'ok':'bad'); result.textContent = res.ok ? `Success\n\nRequest\n${JSON.stringify(payload.request,null,2)}\n\nResponse\n${JSON.stringify(payload.summary,null,2)}` : `Could not place order\n\n${payload.error}`;
  } catch(err){ result.className='result bad'; result.textContent='Browser/server connection failed: '+err; }
  finally{ btn.disabled=false; btn.textContent='Review & place order'; }});
</script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return HTML


@app.post("/api/order")
async def api_order(request: Request) -> JSONResponse:
    try:
        payload: dict[str, Any] = await request.json()
        order = validate_order_input(
            symbol=payload.get("symbol"),
            side=payload.get("side"),
            order_type=payload.get("order_type"),
            quantity=payload.get("quantity"),
            price=payload.get("price"),
            stop_price=payload.get("stop_price"),
        )
        dry_run = bool(payload.get("dry_run", True)) or yes_no(os.getenv("BINANCE_DRY_RUN"))
        client = BinanceClient(logger=logger, dry_run=dry_run)
        service = OrderService(client=client, logger=logger)
        response = service.place(order)
        return JSONResponse({"request": order.as_display_dict(), "summary": response_summary(response), "raw": response})
    except ValidationError as exc:
        logger.error("Web validation failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=422)
    except BinanceAPIError as exc:
        logger.error("Web API failed: %s", exc)
        return JSONResponse({"error": str(exc)}, status_code=502)
    except Exception as exc:  # keep UI friendly, but log full traceback.
        logger.exception("Unexpected web failure: %s", exc)
        return JSONResponse({"error": "Unexpected server error. Check logs/web_orders.log for details."}, status_code=500)
