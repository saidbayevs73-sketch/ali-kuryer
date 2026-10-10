/* Customer storefront, backed by the same orders the staff panels process. */
(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const read=(key,fallback)=>{try{return JSON.parse(localStorage.getItem(key))??fallback}catch{return fallback}};
  const write=(key,value)=>localStorage.setItem(key,JSON.stringify(value));
  let selectedRestaurant=null, selectedCategory='', favorites=read('ali_favorites',[]), favoriteOnly=false;
  let quoteSequence=0, currentQuote=null, orderTimer=null, pending=false;
  const symbols={burger:'🍔',pizza:'🍕',milliy:'🍲',salat:'🥗',ichimlik:'🥤',boshqa:'🍽'};
  function category(f){const n=(f.category||f.name||'').toLowerCase();return /burger/.test(n)?'burger':/pizza|pepperoni|margherita/.test(n)?'pizza':/palov|osh|chuchvara|milliy/.test(n)?'milliy':/salat|achichuk/.test(n)?'salat':/ichimlik|cola|sharbat/.test(n)?'ichimlik':'boshqa'}
  const labels={burger:'Burgerlar',pizza:'Pitsalar',milliy:'Milliy taomlar',salat:'Salatlar',ichimlik:'Ichimliklar',boshqa:'Boshqa taomlar'};
  const image=(url)=>{try{const u=new URL(url);return u.protocol==='https:'?safe(u.href):''}catch{return ''}};
  const post=(path,data)=>requestJSON(API+path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
  function toast(message){$('storeNotice').textContent=message;$('storeNotice').hidden=false;clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('storeNotice').hidden=true,6000)}
  document.body.classList.add('marketplace');
  document.body.insertAdjacentHTML('beforeend','<div id="storeNotice" class="store-notice" role="status" hidden></div><div id="cartShade" class="cart-shade" hidden></div>');
  $('cartShade').onclick=()=>closeCart();
  const ordersButton=document.createElement('button');ordersButton.className='btn btn-black desktop-orders';ordersButton.textContent='Buyurtmalar';ordersButton.onclick=()=>window.openAliOrders();document.querySelector('.header-buttons').prepend(ordersButton);
  document.querySelector('.hero-content').innerHTML='<span class="eyebrow">ALI KURYER • TAOM YETKAZISH</span><h1>Bugun nima<br><span>tanovul qilamiz?</span></h1><p>Oshxonani tanlang. Taomlarni savatga qo‘shing.<br>Buyurtmangiz holatini shu yerda kuzating.</p><button class="btn btn-red" onclick="document.getElementById(\'restaurants\').scrollIntoView({behavior:\'smooth\'})">Menyuni ko‘rish ↗</button><div class="hero-art" aria-hidden="true"><span>🍔</span><span>🍕</span><span>🥗</span><b>Yaxshi taom.<br>Yaxshi kayfiyat.</b></div>';
  document.querySelector('.features').innerHTML='<div class="feature"><b>01 · Tanlang</b>Oshxonalar va taomlar</div><div class="feature"><b>02 · Buyurtma bering</b>Summa oldindan ko‘rsatiladi</div><div class="feature"><b>03 · Kuzating</b>Oshxonadan eshigingizgacha</div>';
  document.querySelector('.search-box').insertAdjacentHTML('afterend','<nav id="categories" class="categories" aria-label="Taom kategoriyalari"></nav><div class="catalog-tools"><button id="allRestaurants" class="filter-chip">Barcha oshxonalar</button><button id="favoriteFilter" class="filter-chip">♡ Sevimlilar</button><select id="menuSort" aria-label="Taomlarni saralash"><option value="default">Menyu tartibi</option><option value="cheap">Avval arzonlari</option><option value="expensive">Avval qimmatlari</option></select></div>');
  $('allRestaurants').onclick=()=>{selectedRestaurant=null;render()};
  $('favoriteFilter').onclick=()=>{favoriteOnly=!favoriteOnly;render()};
  $('menuSort').onchange=()=>render();
  window.render=function(){
    if(!window.aliCatalogLoaded){$('restaurantGrid').innerHTML='<p class="empty">Oshxonalar yuklanmoqda…</p>';$('foodGrid').innerHTML='<p class="empty">Menyu yuklanmoqda…</p>';return}
    const q=$('search').value.trim().toLowerCase();
    const cats=[...new Set(foods.map(category))];
    $('categories').innerHTML=['',...cats].map(c=>`<button class="category-chip ${selectedCategory===c?'active':''}" data-category="${c}" aria-pressed="${selectedCategory===c}"><span>${symbols[c]||'✦'}</span>${labels[c]||'Hammasi'}</button>`).join('');
    $('categories').querySelectorAll('button').forEach(b=>b.onclick=()=>{selectedCategory=b.dataset.category;render()});
    $('favoriteFilter').classList.toggle('active',favoriteOnly);
    $('allRestaurants').textContent=selectedRestaurant?(restaurants.find(r=>r.id===selectedRestaurant)?.name||'Oshxona')+' · Barchasi ×':'Barcha oshxonalar';
    $('restaurantGrid').innerHTML=restaurants.filter(r=>!q||`${r.name} ${r.address}`.toLowerCase().includes(q)||foods.some(f=>f.restaurant_id===r.id&&f.name.toLowerCase().includes(q))).map((r,i)=>`<button class="restaurant-tile tone-${i%3} ${selectedRestaurant===r.id?'selected':''}" data-restaurant="${r.id}"><div class="restaurant-cover"><span>${symbols[category(foods.find(f=>f.restaurant_id===r.id)||{})]}</span><span class="open-badge ${r.accepting_orders?'':'closed'}">${r.accepting_orders?'Buyurtma qabul qilmoqda':'Hozir yopiq'}</span></div><div class="restaurant-info"><h3>${safe(r.name)}</h3><p>${safe(r.address||'Manzil kiritilmagan')}</p><b>Menyuni ko‘rish ↗</b></div></button>`).join('')||'<p class="empty">Mos oshxona topilmadi.</p>';
    $('restaurantGrid').querySelectorAll('button').forEach(b=>b.onclick=()=>{selectedRestaurant=Number(b.dataset.restaurant);render();$('foodGrid').scrollIntoView({behavior:'smooth',block:'start'})});
    let list=foods.filter(f=>(!selectedRestaurant||f.restaurant_id===selectedRestaurant)&&(!selectedCategory||category(f)===selectedCategory)&&(!favoriteOnly||favorites.includes(f.id))&&(!q||`${f.name} ${f.description||''} ${restaurants.find(r=>r.id===f.restaurant_id)?.name||''}`.toLowerCase().includes(q)));
    if($('menuSort').value!=='default')list.sort((a,b)=>($('menuSort').value==='cheap'?1:-1)*(a.price-b.price));
    $('foodGrid').innerHTML=list.map(f=>{const r=restaurants.find(r=>r.id===f.restaurant_id),src=image(f.image_url);return `<article class="food-tile"><div class="food-cover">${src?`<img src="${src}" alt="${safe(f.name)}" loading="lazy">`:`<span class="food-symbol" aria-hidden="true">${symbols[category(f)]}</span><small>Taom rasmi hali qo‘shilmagan</small>`}<button class="favorite-button" data-favorite="${f.id}" aria-label="${safe(f.name)}: sevimlilarga" aria-pressed="${favorites.includes(f.id)}">${favorites.includes(f.id)?'♥':'♡'}</button></div><div class="food-info"><small>${safe(r?.name)}</small><h3>${safe(f.name)}</h3><p>${safe(f.description||f.ingredients||'')}${f.weight?' · '+safe(f.weight):''}</p><div class="food-bottom"><strong>${money(f.price)}</strong><button class="add-food" data-food="${f.id}" ${r?.accepting_orders?'':'disabled'} aria-label="${safe(f.name)} savatga qo‘shish">${r?.accepting_orders?'+':'Yopiq'}</button></div></div></article>`}).join('')||'<div class="empty">Bu tanlovda taom topilmadi. Boshqa kategoriya yoki qidiruvni sinab ko‘ring.</div>';
    $('foodGrid').querySelectorAll('[data-favorite]').forEach(b=>b.onclick=()=>{const id=+b.dataset.favorite;favorites=favorites.includes(id)?favorites.filter(x=>x!==id):[...favorites,id];write('ali_favorites',favorites);render()});
    $('foodGrid').querySelectorAll('[data-food]').forEach(b=>b.onclick=()=>{const f=foods.find(x=>x.id===+b.dataset.food);addCart(f.id,f.name,f.price,f.restaurant_id)});
  };
  window.showRestaurant=async id=>{selectedRestaurant=id;render()};
  const originalAdd=addCart;
  window.addCart=function(...args){const item=cart.find(x=>x.id===args[0]);if(item&&item.qty>=30){toast('Bitta taomdan ko‘pi bilan 30 dona');return}originalAdd(...args)};
  window.changeQty=function(i,amount){if(!cart[i])return;const qty=cart[i].qty+amount;if(qty>30)return;if(qty<=0)cart.splice(i,1);else cart[i].qty=qty;saveCart()};
  const originalOpen=openCart,originalClose=closeCart;
  $('cart').inert=true;
  window.openCart=function(){$('cart').inert=false;originalOpen();$('cartShade').hidden=false;document.body.classList.add('cart-visible')};
  window.closeCart=function(){originalClose();$('cart').inert=true;$('cartShade').hidden=true;document.body.classList.remove('cart-visible')};
  $('cartTotal').insertAdjacentHTML('afterend','<div id="cartBreakdown" class="cart-breakdown" role="status"></div>');
  const originalRenderCart=renderCart;
  window.renderCart=function(){originalRenderCart();currentQuote=null;const sequence=++quoteSequence;if(!cart.length){$('cartBreakdown').textContent='Taom tanlashdan boshlang.';return}$('cartBreakdown').textContent='Yakuniy summa tekshirilmoqda…';post('/api/order-quote',{items:cart.map(x=>({id:Number(x.id),qty:x.qty}))}).then(q=>{if(sequence!==quoteSequence)return;currentQuote=q;$('cartTotal').textContent=money(q.total);$('cartBreakdown').innerHTML=`<div><span>Taomlar</span><b>${money(q.subtotal)}</b></div><div><span>Yetkazish</span><b>${money(q.delivery_fee)}</b></div><p>To‘lov: yetkazilganda naqd.</p>`}).catch(e=>{if(sequence===quoteSequence)$('cartBreakdown').textContent=e.message})};
  const addressFields=['customerName','phone','street','house','entrance','floor','apartment','note'];
  const saved=read('ali_delivery_address',{});
  addressFields.forEach(id=>{if(saved[id])$(id).value=saved[id];$(id).setAttribute('aria-label',$(id).placeholder)});
  $('phone').placeholder='+998 90 123 45 67';
  if(saved.geo&&Number.isFinite(saved.geo.lat)&&Number.isFinite(saved.geo.lng))confirmedLocation=saved.geo;
  window.checkout=async function(button){
    if(pending)return;
    const value=id=>$(id).value.trim();
    if(!cart.length)return toast('Savatga taom qo‘shing.');
    for(const id of ['customerName','phone','street','house'])if(!value(id)){$(id).focus();return toast($(id).placeholder+' maydonini to‘ldiring.')}
    const phone=value('phone').replace(/[\s()-]/g,'');
    if(!/^\+998\d{9}$/.test(phone)){$('phone').focus();return toast('Telefon +998901234567 shaklida bo‘lsin.')}
    if(!confirmedLocation){getLocation();return toast('Yetkazish nuqtasini xaritada tasdiqlang.')}
    if(!currentQuote){renderCart();return toast('Yakuniy summa tekshirilishini kuting.')}
    const payload={name:value('customerName'),phone,street:value('street'),house:value('house'),entrance:value('entrance'),floor:value('floor'),apartment:value('apartment'),address:value('note'),payment:'Naqd',lat:confirmedLocation.lat,lng:confirmedLocation.lng,items:cart.map(x=>({id:Number(x.id),qty:x.qty})),expected_total:currentQuote.total};
    const signature=JSON.stringify(payload),previous=read('ali_pending_order',{});
    payload.request_key=previous.signature===signature?previous.key:crypto.randomUUID();
    write('ali_pending_order',{signature,key:payload.request_key});
    pending=true;button.disabled=true;button.textContent='Buyurtma yuborilmoqda…';
    try{const data=await post('/api/orders',payload);const receipts=read('ali_order_receipts',[]);write('ali_order_receipts',[data.tracking_token,...receipts.filter(t=>t!==data.tracking_token)].slice(0,50));write('ali_delivery_address',Object.assign(Object.fromEntries(addressFields.map(id=>[id,value(id)])),{geo:confirmedLocation}));localStorage.removeItem('ali_pending_order');cart=[];saveCart();closeCart();toast('Buyurtma №'+data.order_id+' qabul qilindi');window.openAliOrders()}
    catch(e){toast(e.message);renderCart()}finally{pending=false;button.disabled=false;button.textContent='Buyurtma berish'}
  };
  // The receipt is a capability: do not look up orders by guessable phone or ID.
  window.openAliOrders=async function(){const dialog=$('aliOrderDialog');if(!dialog)return;dialog.querySelector('p').textContent='Shu brauzerdan berilgan buyurtmalar. Holat har 15 soniyada yangilanadi.';if(!dialog.open)dialog.showModal();await loadOrders();clearInterval(orderTimer);orderTimer=setInterval(()=>{if(dialog.open&&!document.hidden)loadOrders()},15000);dialog.onclose=()=>clearInterval(orderTimer)};
  async function loadOrders(){const box=$('aliOrderList'),tokens=read('ali_order_receipts',[]);if(!tokens.length){box.innerHTML='<div class="empty">Hozircha bu brauzerda saqlangan buyurtma yo‘q. Avvalgi buyurtmaning maxfiy kuzatuv havolasi bo‘lsa, uni oching.</div>';return}
    try{const orders=await post('/api/customer-orders/lookup',{tokens});box.innerHTML=orders.map(o=>{const stages=['Qabul qilindi','Tayyorlanmoqda','Tayyor','Kuryer qabul qildi','Yetkazildi'],index=stages.indexOf(o.status),c=o.courier;return `<article class="receipt"><div class="receipt-heading"><span>BUYURTMA №${o.id}</span><b>${safe(o.restaurant_name)}</b></div><h3>${safe(o.status)}</h3><ol class="order-progress">${stages.map((s,i)=>`<li class="${i<=index?'done':''}" title="${s}"><span>${i+1}</span><small>${['Qabul','Oshxona','Tayyor','Yo‘lda','Yetkazildi'][i]}</small></li>`).join('')}</ol><ul>${o.items.map(x=>`<li>${safe(x.name)} × ${x.qty}<b>${money(x.price*x.qty)}</b></li>`).join('')}</ul><p>${safe(o.address)}</p><div class="receipt-total"><span>Jami · ${safe(o.payment)}</span><b>${money(o.total)}</b></div>${c?`<div class="courier-info"><strong>${safe(c.name)} · Kuryer</strong>${/^\+?\d[\d\s-]{6,20}$/.test(c.phone||'')?`<a href="tel:${safe(c.phone)}">Qo‘ng‘iroq qilish</a>`:''}<p>${c.fresh?'GPS yaqinda yangilandi':'GPS hozir yangilanmayapti'}</p>${o.eta_minutes?`<p>Taxminan ${o.eta_minutes.join('–')} daqiqa. ${safe(o.eta_note)}</p>`:''}</div>`:''}<a class="receipt-track" href="${API}/track/${encodeURIComponent(o.tracking_token)}" target="_blank" rel="noopener noreferrer">Xaritada kuzatish ↗</a><button class="reorder" data-reorder="${o.id}">Qayta buyurtma</button></article>`}).join('')||'<p>Saqlangan buyurtmalar topilmadi.</p>';
      box.querySelectorAll('[data-reorder]').forEach(b=>b.onclick=()=>{const o=orders.find(x=>x.id===+b.dataset.reorder),available=o.items.map(x=>({old:x,food:foods.find(f=>f.id===x.item_id)}));if(available.some(x=>!x.food))return toast('Ba’zi taomlar menyuda yo‘q. Yangilangan menyudan tanlang.');if(cart.length&&!confirm('Joriy savatni ushbu buyurtma bilan almashtirasizmi?'))return;cart=available.map(x=>({id:x.food.id,name:x.food.name,price:x.food.price,restaurantId:x.food.restaurant_id,qty:Math.min(30,x.old.qty)}));saveCart();$('aliOrderDialog').close();openCart()});
    }catch(e){box.textContent='Holatni yangilab bo‘lmadi: '+e.message}}
  // Interactive OpenStreetMap selector with a manual fallback if map assets fail.
  let map=null,marker=null;
  const oldPreview=previewLocation,oldConfirm=confirmLocation;
  window.getLocation=function(){const d=$('locationDialog');if(!d.open)d.showModal();$('locationStatus').textContent='GPS aniqlanmoqda… Xaritadan boshqa nuqta ham tanlashingiz mumkin.';if(window.L){if(!map){$('locationMap').hidden=true;const node=document.createElement('div');node.id='deliveryMap';$('locationMap').before(node);map=L.map(node).setView([41.3111,69.2797],12);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'© OpenStreetMap',maxZoom:19}).addTo(map);map.on('click',e=>setPoint(e.latlng.lat,e.latlng.lng))}setTimeout(()=>map.invalidateSize(),100);if(confirmedLocation)setPoint(confirmedLocation.lat,confirmedLocation.lng)}if(!navigator.geolocation){$('locationStatus').textContent='GPS yo‘q. Xaritadan nuqtani tanlang.';return}navigator.geolocation.getCurrentPosition(p=>{setPoint(p.coords.latitude,p.coords.longitude);$('locationStatus').textContent='Aniqlik: taxminan '+Math.round(p.coords.accuracy)+' m. Nuqtani tekshirib tasdiqlang.'},()=>{$('locationStatus').textContent='GPS ruxsati berilmadi. Xaritadan yetkazish nuqtasini tanlang.'},{enableHighAccuracy:true,timeout:12000,maximumAge:30000})};
  function setPoint(lat,lng){$('locationLat').value=lat;$('locationLng').value=lng;if(map){if(marker)marker.setLatLng([lat,lng]);else marker=L.marker([lat,lng]).addTo(map);map.setView([lat,lng],16)}else oldPreview()}
  window.previewLocation=function(){const p=selectedLocation();if(p)setPoint(p.lat,p.lng);else oldPreview()};
  window.confirmLocation=function(){const p=selectedLocation();if(!p)return toast('Xaritadan nuqta tanlang.');confirmedLocation=p;$('locationDialog').close();toast('Yetkazish nuqtasi tasdiqlandi. Ko‘cha va uy raqamini kiriting.')};
  document.querySelector('#locationDialog>p').textContent='Xaritaga bosib yetkazish nuqtasini tanlang yoki GPS’dan foydalaning.';
  document.addEventListener('keydown',e=>{if(e.key==='Escape')closeCart()});
  render();renderCart();
})();
