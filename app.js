document.addEventListener("DOMContentLoaded",()=>{
 const search=document.getElementById("stockSearch");
 if(search) search.addEventListener("input",()=>{
  const q=search.value.toLowerCase();
  document.querySelectorAll(".stock-row").forEach(row=>{
   const visible=row.innerText.toLowerCase().includes(q);
   row.classList.toggle("hidden",!visible);
   const next=row.nextElementSibling;
   if(next&&next.classList.contains("trade-row")) next.classList.add("hidden");
  });
 });
 document.querySelectorAll(".trade-toggle").forEach(btn=>btn.addEventListener("click",event=>{
  event.stopPropagation();
  const row=document.getElementById("trade-"+btn.dataset.ticker);
  if(row) row.classList.toggle("hidden");
 }));

 // Stock details modal: click or keyboard-activate any stock row.
 const backdrop=document.getElementById("stockDetailsBackdrop");
 const closeButton=document.getElementById("closeStockDetails");
 const closeModal=()=>{backdrop.classList.add("hidden");};
 const money=value=>new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(Number(value||0));
 const openDetails=row=>{
  document.getElementById("stockDetailsTitle").textContent=row.dataset.ticker||"Stock details";
  document.getElementById("stockDetailsCompany").textContent=row.dataset.company||"";
  document.getElementById("stockDetailsPrice").textContent=money(row.dataset.price);
  document.getElementById("detailTicker").textContent=row.dataset.ticker||"—";
  document.getElementById("detailVolume").textContent=Number(row.dataset.volume||0).toLocaleString("en-US");
  document.getElementById("detailMarketCap").textContent=money(row.dataset.marketCap);
  document.getElementById("detailOpen").textContent=money(row.dataset.open);
  document.getElementById("detailHigh").textContent=money(row.dataset.high);
  document.getElementById("detailLow").textContent=money(row.dataset.low);
  backdrop.classList.remove("hidden");
  closeButton.focus();
 };
 document.querySelectorAll(".stock-detail-trigger").forEach(row=>{
  row.addEventListener("click",event=>{if(!event.target.closest("button")) openDetails(row);});
  row.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();openDetails(row);}});
 });
 closeButton.addEventListener("click",closeModal);
 document.getElementById("doneStockDetails").addEventListener("click",closeModal);
 backdrop.addEventListener("click",event=>{if(event.target===backdrop) closeModal();});
 document.addEventListener("keydown",event=>{if(event.key==="Escape"&&!backdrop.classList.contains("hidden")) closeModal();});

 // Poll the latest simulated prices every five seconds without reloading the page.
 const refreshMarketPrices=async()=>{
  if(document.visibilityState!=="visible") return;
  try{
   const response=await fetch("/api/market-data",{headers:{"Accept":"application/json"}});
   if(!response.ok) return;
   const stocks=await response.json();
   stocks.forEach(stock=>{
    const row=[...document.querySelectorAll(".stock-detail-trigger")].find(item=>item.dataset.ticker===stock.ticker);
    if(!row) return;
    row.dataset.price=stock.current_price;
    row.dataset.volume=stock.available_volume;
    row.dataset.marketCap=stock.market_cap;
    row.dataset.open=stock.opening_price;
    row.dataset.high=stock.day_high;
    row.dataset.low=stock.day_low;
    const cells=row.querySelectorAll("td");
    if(cells[1]) cells[1].textContent=money(stock.current_price);
    if(cells[2]) cells[2].textContent=Number(stock.available_volume).toLocaleString("en-US");
    if(cells[3]) cells[3].textContent=money(stock.market_cap);
    if(cells[4]) cells[4].textContent=money(stock.opening_price);
    if(cells[5]) cells[5].textContent=money(stock.day_high);
    if(cells[6]) cells[6].textContent=money(stock.day_low);
    const tradePrice=row.nextElementSibling?.querySelector(".trade-form span b");
    if(tradePrice) tradePrice.textContent=money(stock.current_price);
   });
   // Keep an already-open details dialog in sync with the latest market data.
   const selected=document.getElementById("stockDetailsTitle").textContent;
   const active=[...document.querySelectorAll(".stock-detail-trigger")].find(row=>row.dataset.ticker===selected);
   if(active&&!backdrop.classList.contains("hidden")){
    document.getElementById("stockDetailsPrice").textContent=money(active.dataset.price);
    document.getElementById("detailVolume").textContent=Number(active.dataset.volume||0).toLocaleString("en-US");
    document.getElementById("detailMarketCap").textContent=money(active.dataset.marketCap);
    document.getElementById("detailOpen").textContent=money(active.dataset.open);
    document.getElementById("detailHigh").textContent=money(active.dataset.high);
    document.getElementById("detailLow").textContent=money(active.dataset.low);
   }
  }catch(error){console.warn("Could not refresh market prices:",error);}
 };
 refreshMarketPrices();
 setInterval(refreshMarketPrices,5000);
});
