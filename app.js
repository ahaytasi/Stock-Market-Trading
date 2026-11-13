const stocks = [
 {ticker:"AAPL",company:"Apple Inc.",price:228.45,open:226.10,high:229.12,low:225.50,volume:42500000,shares:50,color:"#20252d"},
 {ticker:"MSFT",company:"Microsoft Corp.",price:412.17,open:409.80,high:413.25,low:408.12,volume:28700000,shares:20,color:"#2877c7"},
 {ticker:"GOOGL",company:"Alphabet Inc.",price:182.34,open:183.20,high:184.10,low:181.50,volume:24300000,shares:0,color:"#4285f4"},
 {ticker:"AMZN",company:"Amazon.com Inc.",price:205.67,open:203.90,high:207.10,low:203.40,volume:32100000,shares:0,color:"#f39b32"},
 {ticker:"TSLA",company:"Tesla Inc.",price:346.21,open:349.00,high:351.20,low:344.70,volume:45800000,shares:0,color:"#d84a4a"},
 {ticker:"NVDA",company:"NVIDIA Corp.",price:141.88,open:140.50,high:143.20,low:139.90,volume:51200000,shares:0,color:"#76a842"}
];
let selected = stocks[0], side = "buy", cash = 25000;
const transactions = [];
const histories = Object.fromEntries(stocks.map(s=>[s.ticker,Array.from({length:24},(_,i)=>s.open+(s.price-s.open)*i/23+(Math.random()-.5)*1.4)]));
const money = n => n.toLocaleString("en-US",{style:"currency",currency:"USD"});
const number = n => n.toLocaleString("en-US");
const cap = s => s.price*s.volume;
const changePct = s => ((s.price-s.open)/s.open)*100;
function showView(name){
 document.querySelectorAll(".view").forEach(v=>v.classList.add("hidden"));
 document.getElementById(name+"View").classList.remove("hidden");
 document.querySelectorAll(".nav-link").forEach(b=>b.classList.toggle("active",b.dataset.view===name));
 document.querySelector(".main-nav").classList.remove("open");
 if(name==="portfolio") renderPortfolio();
 if(name==="transactions") renderTransactions();
}
document.querySelectorAll(".nav-link").forEach(b=>b.addEventListener("click",()=>showView(b.dataset.view)));
document.getElementById("mobileMenu").addEventListener("click",()=>document.querySelector(".main-nav").classList.toggle("open"));
function renderMarket(){
 const query=document.getElementById("stockSearch").value.toLowerCase();
 document.getElementById("stockRows").innerHTML=stocks.filter(s=>(s.ticker+s.company).toLowerCase().includes(query)).map(s=>{
  const ch=changePct(s), sign=ch>=0?"+":"";
  return `<tr><td><div class="stock-name"><span class="stock-logo">${s.ticker.slice(0,1)}</span><span><b>${s.ticker}</b><small>${s.company}</small></span></div></td><td><b>${money(s.price)}</b></td><td class="change ${ch>=0?"positive":"negative"}">${ch>=0?"▲":"▼"} ${sign}${ch.toFixed(2)}%</td><td>${number(s.volume)}</td><td>${money(cap(s))}</td><td>${money(s.open)}</td><td>${money(s.high)}</td><td>${money(s.low)}</td><td><button class="text-btn" data-stock="${s.ticker}">Details</button></td></tr>`;
 }).join("")||`<tr><td colspan="9" class="empty-state">No matching stocks found.</td></tr>`;
 document.querySelectorAll("[data-stock]").forEach(b=>b.addEventListener("click",()=>openDetail(b.dataset.stock)));
 document.getElementById("listedCount").textContent=stocks.length;
 document.getElementById("totalCap").textContent=compactMoney(stocks.reduce((a,s)=>a+cap(s),0));
 document.getElementById("advancing").textContent=stocks.filter(s=>changePct(s)>=0).length;
 document.getElementById("declining").textContent=stocks.filter(s=>changePct(s)<0).length;
}
function compactMoney(n){return n>=1e12?"$"+(n/1e12).toFixed(2)+"T":n>=1e9?"$"+(n/1e9).toFixed(2)+"B":money(n)}
document.getElementById("stockSearch").addEventListener("input",renderMarket);
function openDetail(ticker){selected=stocks.find(s=>s.ticker===ticker);showView("detail");renderDetail();}
function renderDetail(){
 const s=selected,ch=changePct(s),sign=ch>=0?"+":"";
 document.getElementById("detailCompany").textContent=s.company;
 document.getElementById("detailTicker").textContent=s.ticker;
 document.getElementById("detailPrice").textContent=money(s.price);
 const c=document.getElementById("detailChange");c.textContent=`${sign}${ch.toFixed(2)}% (${ch>=0?"+":""}${money(s.price-s.open)})`;c.className=ch>=0?"positive":"negative";
 document.getElementById("detailOpen").textContent=money(s.open);document.getElementById("detailHigh").textContent=money(s.high);document.getElementById("detailLow").textContent=money(s.low);document.getElementById("detailVolume").textContent=number(s.volume);document.getElementById("detailCap").textContent=compactMoney(cap(s));
 updateEstimate();drawChart(document.getElementById("detailChart"),histories[s.ticker]);
}
function updateEstimate(){const q=Math.max(0,Number(document.getElementById("shareQuantity").value)||0);document.getElementById("orderEstimate").textContent=money(q*selected.price);}
document.getElementById("shareQuantity").addEventListener("input",updateEstimate);
document.querySelectorAll(".order-tab").forEach(b=>b.addEventListener("click",()=>{side=b.dataset.side;document.querySelectorAll(".order-tab").forEach(x=>x.classList.toggle("selected",x===b));document.getElementById("placeOrder").textContent=`Place ${side==="buy"?"Buy":"Sell"} Order`;document.getElementById("orderMessage").textContent="";updateEstimate();}));
document.getElementById("placeOrder").addEventListener("click",()=>{
 const q=Math.floor(Number(document.getElementById("shareQuantity").value)),total=q*selected.price,msg=document.getElementById("orderMessage");
 msg.className="message";
 if(!Number.isFinite(q)||q<1){msg.textContent="Enter a share quantity of at least 1.";msg.classList.add("error");return;}
 if(side==="buy"&&total>cash){msg.textContent="Insufficient cash balance for this order.";msg.classList.add("error");return;}
 if(side==="sell"&&q>selected.shares){msg.textContent=`You only own ${selected.shares} ${selected.ticker} shares in this demo portfolio.`;msg.classList.add("error");return;}
 if(side==="buy"){cash-=total;selected.shares+=q;}else{cash+=total;selected.shares-=q;}
 transactions.unshift({time:new Date().toLocaleString(),type:side.toUpperCase(),ticker:selected.ticker,shares:q,price:selected.price,total,status:"Executed"});
 msg.textContent=`Demo ${side} order executed: ${q} ${selected.ticker} shares at ${money(selected.price)}.`;msg.classList.add("success");renderPortfolio();renderTransactions();
});
document.getElementById("backToMarket").addEventListener("click",()=>showView("market"));
function renderPortfolio(){
 document.getElementById("cashBalance").textContent=money(cash);
 const holdings=stocks.filter(s=>s.shares>0);
 document.getElementById("holdingsValue").textContent=money(holdings.reduce((a,s)=>a+s.shares*s.price,0));
 document.getElementById("holdingRows").innerHTML=holdings.map(s=>`<tr><td><b>${s.ticker}</b> · ${s.company}</td><td>${number(s.shares)}</td><td>${money(s.price)}</td><td>${money(s.shares*s.price)}</td></tr>`).join("")||`<tr><td colspan="4" class="empty-state">No stock holdings yet.</td></tr>`;
}
function renderTransactions(){document.getElementById("transactionRows").innerHTML=transactions.map(t=>`<tr><td>${t.time}</td><td class="${t.type==="BUY"?"positive":"negative"}">${t.type}</td><td>${t.ticker}</td><td>${number(t.shares)}</td><td>${money(t.price)}</td><td>${money(t.total)}</td><td>${t.status}</td></tr>`).join("")||`<tr><td colspan="7" class="empty-state">No transactions yet.</td></tr>`;}
function drawChart(canvas,values){
 if(!canvas)return;const rect=canvas.getBoundingClientRect(),w=Math.max(280,rect.width),h=canvas.id==="detailChart"?260:170,dpr=window.devicePixelRatio||1;
 canvas.width=w*dpr;canvas.height=h*dpr;canvas.style.height=h+"px";const ctx=canvas.getContext("2d");ctx.scale(dpr,dpr);ctx.clearRect(0,0,w,h);
 const min=Math.min(...values)-.5,max=Math.max(...values)+.5,pad={l:42,r:12,t:12,b:24},cw=w-pad.l-pad.r,ch=h-pad.t-pad.b;
 ctx.font="10px Inter,Arial";ctx.fillStyle="#8390a2";ctx.strokeStyle="#edf1f6";ctx.lineWidth=1;
 for(let i=0;i<4;i++){const y=pad.t+ch*i/3;ctx.beginPath();ctx.moveTo(pad.l,y);ctx.lineTo(w-pad.r,y);ctx.stroke();ctx.fillText((max-(max-min)*i/3).toFixed(1),3,y+3);}
 const pts=values.map((v,i)=>({x:pad.l+cw*i/(values.length-1),y:pad.t+ch*(max-v)/(max-min)}));
 const grad=ctx.createLinearGradient(0,pad.t,0,h);grad.addColorStop(0,"rgba(23,105,210,.22)");grad.addColorStop(1,"rgba(23,105,210,0)");
 ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.lineTo(pts.at(-1).x,pad.t+ch);ctx.lineTo(pts[0].x,pad.t+ch);ctx.closePath();ctx.fillStyle=grad;ctx.fill();
 ctx.beginPath();pts.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.strokeStyle="#1769d2";ctx.lineWidth=2.5;ctx.stroke();
 ["9 AM","11 AM","1 PM","3 PM"].forEach((t,i)=>{ctx.fillStyle="#8390a2";ctx.fillText(t,pad.l+cw*i/3-10,h-5);});
}
function tick(){
 stocks.forEach(s=>{const drift=(Math.random()-.49)*.24;s.price=Math.max(.5,s.price+drift);s.high=Math.max(s.high,s.price);s.low=Math.min(s.low,s.price);histories[s.ticker].push(s.price);if(histories[s.ticker].length>24)histories[s.ticker].shift();});
 renderMarket();if(!document.getElementById("detailView").classList.contains("hidden"))renderDetail();
}
renderMarket();renderPortfolio();drawChart(document.getElementById("marketChart"),histories.AAPL);renderTransactions();
window.addEventListener("resize",()=>{drawChart(document.getElementById("marketChart"),histories.AAPL);if(!document.getElementById("detailView").classList.contains("hidden"))drawChart(document.getElementById("detailChart"),histories[selected.ticker]);});
setInterval(tick,3000);
