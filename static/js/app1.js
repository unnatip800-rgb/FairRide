let rideType="FairGo",fare=180,booking=null,timer=null,etaTimer=null,start=Date.now(),saved=null;
const session="FR-"+Math.random().toString(36).slice(2,9),$=id=>document.getElementById(id);
const mmss=n=>String(Math.floor(n/60)).padStart(2,"0")+":"+String(n%60).padStart(2,"0");
function goBook(){$("booking").scrollIntoView({behavior:"smooth"})}
function toast(s){let t=$("toast");t.textContent=s;t.classList.add("show");setTimeout(()=>t.classList.remove("show"),2500)}
function log(type,value,duration=null){fetch("/api/event",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_id:session,event_type:type,event_value:value,duration_seconds:duration})}).catch(()=>{})}
async function post(url,data){let r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({session_id:session,...data})}),j=await r.json();if(!r.ok)throw Error(j.error||"Request failed");return j}
async function getj(url){let r=await fetch(url),j=await r.json();if(!r.ok)throw Error(j.error||"Request failed");return j}
document.querySelectorAll(".ride").forEach(b=>b.onclick=()=>{document.querySelectorAll(".ride").forEach(x=>x.classList.remove("chosen"));b.classList.add("chosen");rideType=b.dataset.type;fare=+b.dataset.fare;log("ride_selected",rideType)});
$("lockopt").onchange=e=>log("lock_option_toggled",e.target.checked?"on":"off");

async function bookRide(){let pickup=$("pickup").value.trim(),destination=$("destination").value.trim();if(!pickup||!destination){toast("Enter pickup and destination.");log("validation_error","missing_location");return}
try{booking=await post("/api/book",{pickup,destination,ride_type:rideType,lock_enabled:$("lockopt").checked});saved={pickup,destination};
$("from").textContent=pickup;$("to").textContent=destination;$("fare").textContent="₹"+booking.fare;$("farelabel").textContent="ORIGINAL FARE";$("driver").textContent=booking.driver;$("avatar").textContent=booking.driver[0];
$("rideheading").textContent="Driver assigned";$("status").textContent="● Driver assigned";
["recovery","cancelbox","cancelled","delayalert"].forEach(i=>$(i).classList.add("hide"));$("rideactions").classList.remove("hide");$("eta").classList.remove("hide");
if(timer)clearInterval(timer);startETA();$("ridebox").classList.remove("hide");$("ridebox").scrollIntoView({behavior:"smooth"});start=Date.now();toast("Demo booking created.");metrics()}catch(e){toast(e.message)}}

function startETA(){if(etaTimer)clearInterval(etaTimer);let n=180;$("etatime").textContent="3:00";
etaTimer=setInterval(()=>{n--;$("etatime").textContent=Math.floor(n/60)+":"+String(n%60).padStart(2,"0");if(n<=0){clearInterval(etaTimer);simulateDelay(true)}},1000)}
async function simulateDelay(auto){if(!booking)return;try{await post("/api/delay",{booking_id:booking.id});if(etaTimer)clearInterval(etaTimer);$("etatime").textContent="delayed";$("delayalert").classList.remove("hide");toast(auto===true?"Delay Alert: driver is late.":"Delay Alert shown (demo).");metrics()}catch(e){toast(e.message)}}

async function openCancel(){if(!booking)return;try{let r=await getj("/api/cancel-fee?booking_id="+booking.id);$("feeamt").textContent="₹"+r.fee;$("feewhy").textContent=r.why;$("cancelbox").classList.remove("hide");$("cancelbox").scrollIntoView({behavior:"smooth",block:"center"});log("fee_explainer_viewed","fee="+r.fee)}catch(e){toast(e.message)}}
function closeCancel(){$("cancelbox").classList.add("hide")}
async function confirmCancel(){try{let r=await post("/api/cancel-user",{booking_id:booking.id});if(etaTimer)clearInterval(etaTimer);closeCancel();$("rideactions").classList.add("hide");$("eta").classList.add("hide");$("delayalert").classList.add("hide");
$("status").textContent="● Cancelled by you";$("rideheading").textContent="Ride cancelled";$("cancelledmsg").textContent=r.fee?"Cancellation fee: ₹"+r.fee:"No cancellation fee charged.";$("cancelled").classList.remove("hide");toast("Ride cancelled.");metrics()}catch(e){toast(e.message)}}
function bookAgain(){if(saved){$("pickup").value=saved.pickup;$("destination").value=saved.destination}bookRide()}

async function cancelDriver(){if(!booking)return;try{let s=await post("/api/cancel-driver",{booking_id:booking.id});if(etaTimer)clearInterval(etaTimer);$("status").textContent="● Driver cancelled";$("rideheading").textContent="Your driver cancelled";$("rideactions").classList.add("hide");$("eta").classList.add("hide");$("delayalert").classList.add("hide");closeCancel();
renderRecovery(s);$("recovery").classList.remove("hide");$("recovery").scrollIntoView({behavior:"smooth"});metrics();toast(s.lock_active?"FairFare Lock activated.":"Driver cancelled.")}catch(e){toast(e.message)}}
function renderRecovery(s){if(timer)clearInterval(timer);$("old").textContent="₹"+s.next_lock_fare;$("new").textContent="₹"+(s.lock_active?s.quote:Math.round(s.next_lock_fare*(s.lock_count?1.1:1.22)));
$("saved").textContent="₹"+(s.lock_active?s.savings:0);
if(s.lock_active){$("oldlabel").textContent="Protected fare";$("old").textContent="₹"+s.locked_fare;$("new").textContent="₹"+s.quote;$("lockstate").textContent="♢ FairFare Lock active";$("locktext").textContent="Fare ₹"+s.locked_fare+" protected for 10 minutes.";$("lockbtn").classList.add("hide");$("timer").classList.remove("hide");countdown(s.seconds_left)}
else{$("oldlabel").textContent="Fare you can lock";$("lockstate").textContent=s.lock_count?"♢ FairFare Lock expired":"♢ FairFare Lock not active";$("locktext").textContent=s.lock_count?"Fare has increased. Lock ₹"+s.next_lock_fare+" again for another 10 minutes.":"Lock ₹"+s.next_lock_fare+" for 10 minutes while you rebook.";
$("lockbtn").textContent=s.lock_count?"Lock again at ₹"+s.next_lock_fare+" (10 min)":"Activate FairFare Lock (10 min)";$("lockbtn").classList.remove("hide");$("timer").classList.add("hide");$("saved").textContent="₹0";$("new").textContent="₹"+s.quote}}
function countdown(sec){let end=Date.now()+sec*1000;function tick(){let n=Math.max(0,Math.ceil((end-Date.now())/1000));$("timer").textContent=mmss(n);if(!n){clearInterval(timer);refresh()}}tick();timer=setInterval(tick,1000)}
async function refresh(){try{renderRecovery(await getj("/api/booking/"+booking.id));log("lock_expired",booking.id);toast("FairFare Lock expired. You can lock again.");metrics()}catch(e){}}
async function lockNow(){try{renderRecovery(await post("/api/lock",{booking_id:booking.id}));toast("FairFare Lock activated for 10 minutes.");metrics()}catch(e){toast(e.message)}}
async function rebook(){try{let r=await post("/api/rebook",{booking_id:booking.id});if(timer)clearInterval(timer);$("driver").textContent=r.driver;$("avatar").textContent=r.driver[0];$("fare").textContent="₹"+r.payable_fare;$("farelabel").textContent="PAYABLE FARE";$("rideheading").textContent="Replacement ride assigned";$("status").textContent="● Replacement assigned";$("recovery").classList.add("hide");$("ridebox").scrollIntoView({behavior:"smooth"});log("rebooking_completed",booking.id,(Date.now()-start)/1000);toast(r.savings?"Rebooked! You saved ₹"+r.savings:"Rebooked at ₹"+r.payable_fare);metrics()}catch(e){toast(e.message)}}
async function sendReport(e){e.preventDefault();try{let r=await post("/api/report",{booking_id:booking?.id||null,category:$("category").value,details:$("details").value});$("reportmsg").textContent="Report #"+r.id+" received. Status: "+r.status;document.querySelector("form").reset();log("report_submitted",r.id);metrics();toast("Demo report submitted.")}catch(e){$("reportmsg").textContent=e.message}}
async function metrics(){try{let s=await getj("/api/measurements");const set=(i,v)=>$(i).textContent=v;
set("mbook",s.bookings);set("mlock",s.locks);set("mdc",s.driver_cancels);set("muc",s.user_cancels);set("mdelay",s.delay_alerts);set("mwaive",s.fees_waived);set("mreport",s.reports);set("mrec",s.avg_recovery+"s");set("mevent",s.events);
set("msince",s.since?"Recording since "+s.since.replace("T"," "):"No data recorded yet.");
$("mlog").innerHTML=s.recent.map(x=>"<li><span>"+x.created_at.slice(5).replace("T"," ")+"</span><b>"+x.event_type.replace(/_/g," ")+"</b><i>"+String(x.event_value).replace(/</g,"&lt;")+"</i></li>").join("")}catch(e){}}
document.addEventListener("click",e=>{if(e.target.closest("button,a"))log("click",e.target.closest("button,a").innerText.trim().slice(0,80))});metrics();
