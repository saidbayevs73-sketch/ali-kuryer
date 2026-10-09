"use strict";

// Public customer view; all totals and order permissions are checked by the server.
const byId = (id) => document.getElementById(id);
const uzs = (value) => new Intl.NumberFormat("uz-UZ").format(Number(value) || 0) + " so‘m";

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = result.detail || result.error || "Server bilan aloqa bo‘lmadi";
    throw new Error(typeof detail === "string" ? detail : "Ma’lumotlarni tekshiring");
  }
  return result;
}

function postJSON(path, data, token) {
  const headers = {"Content-Type": "application/json"};
  if (token) headers.Authorization = "Bearer " + token;
  return api(path, {method: "POST", headers, body: JSON.stringify(data)});
}

function readSaved(key, fallback) {
  try { return JSON.parse(localStorage.getItem(key)) || fallback; }
  catch { return fallback; }
}

let restaurants = [];
let selectedRestaurant = null;
let cart = readSaved("ali_customer_cart", []);
if (!Array.isArray(cart)) cart = [];
let lastOrder = readSaved("ali_customer_last_order", null);
let deliveryLocation = null;
let map = null;
let marker = null;

function button(text, onClick, style) {
  const b = document.createElement("button");
  b.type = "button";
  b.textContent = text;
  if (style) b.className = style;
  b.addEventListener("click", onClick);
  return b;
}

function saveCart() {
  localStorage.setItem("ali_customer_cart", JSON.stringify(cart));
  renderCart();
}

function renderCart() {
  const container = byId("cart-items");
  if (!container) return;
  container.replaceChildren();
  if (cart.length === 0) {
    container.textContent = "Savatcha bo‘sh. Yuqoridan taom tanlang.";
  }
  let total = 0;
  for (const item of cart) {
    total += item.price * item.qty;
    const row = document.createElement("div");
    row.className = "cart-item";
    const description = document.createElement("span");
    description.textContent = item.name + " • " + uzs(item.price * item.qty);
    const actions = document.createElement("div");
    actions.className = "cart-actions";
    actions.append(
      button("−", () => changeQty(item.id, -1)),
      document.createTextNode(String(item.qty)),
      button("+", () => changeQty(item.id, 1))
    );
    row.append(description, actions);
    container.append(row);
  }
  byId("cart-total").textContent = uzs(total);
}

function changeQty(id, change) {
  const item = cart.find((entry) => entry.id === id);
  if (!item) return;
  item.qty += change;
  if (item.qty <= 0) cart = cart.filter((entry) => entry.id !== id);
  if (item.qty > 30) item.qty = 30;
  saveCart();
}

function addToCart(food, restaurantId) {
  if (cart.length && cart[0].restaurantId !== restaurantId) {
    if (!confirm("Savatchadagi boshqa oshxona taomlarini o‘chirib, yangisini tanlaysizmi?")) return;
    cart = [];
  }
  let item = cart.find((entry) => entry.id === food.id);
  if (item) {
    item.qty = Math.min(30, item.qty + 1);
  } else {
    cart.push({
      id: food.id, name: food.name, price: Number(food.price),
      restaurantId, qty: 1,
    });
  }
  saveCart();
  byId("checkout").scrollIntoView({behavior: "smooth"});
}

async function showMenu(restaurant) {
  selectedRestaurant = restaurant;
  const target = byId("menu-list");
  const status = byId("menu-message");
  target.replaceChildren();
  status.textContent = "Menyu yuklanmoqda…";
  try {
    const data = await api("/api/customer/restaurants/" + restaurant.id + "/menu");
    const menu = Array.isArray(data.items) ? data.items : [];
    status.textContent = restaurant.name + (menu.length ? "" : " — taom yo‘q");
    for (const food of menu) {
      const card = document.createElement("article");
      card.className = "food-card";
      if (food.image_url && /^https:\/\//.test(food.image_url)) {
        const photo = document.createElement("img");
        photo.src = food.image_url;
        photo.alt = food.name;
        photo.loading = "lazy";
        photo.referrerPolicy = "no-referrer";
        card.append(photo);
      }
      const title = document.createElement("h3");
      title.textContent = food.name;
      const price = document.createElement("p");
      price.className = "price";
      price.textContent = uzs(food.price);
      const add = button("+ Savatga", () => addToCart(food, restaurant.id));
      add.disabled = !restaurant.is_approved;
      if (add.disabled) add.title = "Oshxona hali tasdiqlanmagan";
      card.append(title, price, add);
      target.append(card);
    }
    byId("menu-section").scrollIntoView({behavior: "smooth"});
  } catch (error) {
    status.textContent = error.message;
  }
}

async function loadRestaurants() {
  const container = byId("restaurant-list");
  if (!container) return;
  try {
    restaurants = await api("/api/customer/restaurants");
    if (!restaurants.length) byId("restaurant-message").textContent = "Hozircha oshxona yo‘q.";
    for (const restaurant of restaurants) {
      const card = document.createElement("article");
      card.className = "restaurant-card";
      const title = document.createElement("h3");
      title.textContent = restaurant.name;
      const address = document.createElement("p");
      address.textContent = restaurant.address || "Manzil kiritilmagan";
      const menuButton = button("Menyuni ko‘rish", () => showMenu(restaurant));
      card.append(title, address, menuButton);
      if (!restaurant.is_approved) {
        const note = document.createElement("p");
        note.textContent = "Buyurtma qabul qilish hali faollashtirilmagan";
        card.append(note);
      }
      container.append(card);
    }
  } catch (error) {
    byId("restaurant-message").textContent = error.message;
  }
}

function selectLocation(lat, lng) {
  deliveryLocation = {lat, lng};
  byId("location-status").textContent =
    "✅ Manzil belgilandi: " + lat.toFixed(6) + ", " + lng.toFixed(6);
  if (map && window.L) {
    const point = [lat, lng];
    if (marker) marker.setLatLng(point);
    else marker = window.L.marker(point).addTo(map);
    map.setView(point, 17);
  }
}

function initMap() {
  const element = byId("delivery-map");
  if (!element) return;
  if (!window.L) {
    element.textContent = "Xarita yuklanmadi. GPS tugmasini ishlatib ko‘ring.";
    return;
  }
  // Initial viewport is illustrative, NOT the customer's detected location.
  map = window.L.map(element).setView([40.997, 71.672], 12);
  window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  }).addTo(map);
  map.on("click", (event) => selectLocation(event.latlng.lat, event.latlng.lng));
}

function useGPS() {
  if (!navigator.geolocation) {
    byId("location-status").textContent = "GPS bu qurilmada ishlamaydi. Xaritadan tanlang.";
    return;
  }
  const status = byId("location-status");
  status.textContent = "GPS qidirilmoqda…";
  navigator.geolocation.getCurrentPosition(
    (position) => selectLocation(position.coords.latitude, position.coords.longitude),
    () => { status.textContent = "GPS ruxsatini tekshiring yoki xaritadan joyni bosing."; },
    {enableHighAccuracy: true, timeout: 15000, maximumAge: 0}
  );
}

async function placeOrder(event) {
  event.preventDefault();
  const status = byId("checkout-status");
  status.textContent = "";
  if (!cart.length) { status.textContent = "Avval taom tanlang."; return; }
  if (!deliveryLocation) { status.textContent = "Xaritadan yetkazish joyini belgilang."; return; }
  const submit = byId("order-submit");
  submit.disabled = true;
  status.textContent = "Buyurtma yuborilmoqda…";
  const payload = {
    name: byId("customer-name").value.trim(),
    phone: byId("customer-phone").value.trim(),
    street: byId("street").value.trim(),
    house: byId("house").value.trim(),
    entrance: byId("entrance").value.trim(),
    floor: byId("floor").value.trim(),
    apartment: byId("apartment").value.trim(),
    note: byId("note").value.trim(),
    lat: deliveryLocation.lat,
    lng: deliveryLocation.lng,
    payment: "cash",
    items: cart.map((item) => ({id: item.id, qty: item.qty})),
  };
  try {
    const result = await postJSON("/api/orders", payload);
    lastOrder = {id: result.order_id, token: result.tracking_token, phone: payload.phone};
    localStorage.setItem("ali_customer_last_order", JSON.stringify(lastOrder));
    localStorage.setItem("ali_customer_name", JSON.stringify(payload.name));
    cart = [];
    saveCart();
    byId("complaint-name").value = payload.name;
    byId("complaint-phone").value = payload.phone;
    status.textContent = "✅ Buyurtma №" + result.order_id + " qabul qilindi. Jami: " + uzs(result.total);
    await trackOrder();
    byId("tracking").scrollIntoView({behavior: "smooth"});
  } catch (error) {
    status.textContent = "Xatolik: " + error.message;
  } finally {
    submit.disabled = false;
  }
}

async function trackOrder() {
  const target = byId("order-information");
  if (!lastOrder?.id || !lastOrder.token) {
    target.textContent = "Hozircha kuzatiladigan buyurtma yo‘q.";
    return;
  }
  target.textContent = "Buyurtma holati tekshirilmoqda…";
  try {
    const result = await postJSON("/api/orders/" + lastOrder.id + "/track", {
      token: lastOrder.token,
    });
    const statuses = {
      pending: "Qabul qilindi", preparing: "Tayyorlanmoqda",
      ready: "Kuryer kutilmoqda", picked_up: "Kuryer qabul qildi",
      on_the_way: "Yo‘lda", delivered: "Yetkazildi", canceled: "Bekor qilindi",
    };
    target.textContent = "Buyurtma №" + result.order_id + " • " +
      (statuses[result.status] || result.status) + " • " + uzs(result.total);
    if (result.courier_location) {
      const p = result.courier_location;
      const link = document.createElement("a");
      link.href = "https://www.openstreetmap.org/?mlat=" + encodeURIComponent(p.lat) +
        "&mlon=" + encodeURIComponent(p.lng) + "#map=17/" +
        encodeURIComponent(p.lat) + "/" + encodeURIComponent(p.lng);
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = " • Kuryerni xaritada ko‘rish";
      target.append(link);
    }
  } catch (error) {
    target.textContent = error.message;
  }
}

async function submitComplaint(event) {
  event.preventDefault();
  const status = byId("complaint-status");
  const payload = {
    name: byId("complaint-name").value.trim(),
    phone: byId("complaint-phone").value.trim(),
    message: byId("complaint-message").value.trim(),
  };
  if (lastOrder?.id && lastOrder.token && lastOrder.phone === payload.phone) {
    payload.order_id = lastOrder.id;
    payload.tracking_token = lastOrder.token;
  }
  status.textContent = "Murojaat yuborilmoqda…";
  try {
    const result = await postJSON("/api/customer/complaints", payload);
    status.textContent = "✅ Murojaat №" + result.complaint_id + " adminga yuborildi.";
    byId("complaint-message").value = "";
  } catch (error) {
    status.textContent = error.message;
  }
}

function startCustomer() {
  if (!byId("restaurant-list")) return;
  loadRestaurants();
  renderCart();
  initMap();
  if (lastOrder) {
    byId("complaint-phone").value = lastOrder.phone || "";
    byId("customer-phone").value = lastOrder.phone || "";
    const savedName = readSaved("ali_customer_name", "");
    byId("customer-name").value = savedName;
    byId("complaint-name").value = savedName;
  }
  byId("gps-btn").addEventListener("click", useGPS);
  byId("checkout-form").addEventListener("submit", placeOrder);
  byId("track-btn").addEventListener("click", trackOrder);
  byId("complaint-form").addEventListener("submit", submitComplaint);
  trackOrder();
}

startCustomer();


function adminToken() { return sessionStorage.getItem("ali_admin_token") || ""; }

async function loadAdminComplaints() {
  const target = byId("admin-complaints");
  const token = adminToken();
  target.textContent = "Murojaatlar yuklanmoqda…";
  try {
    const items = await api("/api/admin/complaints", {
      headers: {Authorization: "Bearer " + token},
    });
    byId("admin-login-form").hidden = true;
    byId("admin-workspace").hidden = false;
    target.replaceChildren();
    if (!items.length) target.textContent = "Hozircha murojaatlar yo‘q.";
    for (const item of items) {
      const card = document.createElement("article");
      card.className = "white-panel";
      const title = document.createElement("h3");
      title.textContent = "Murojaat №" + item.id + " • " + item.status;
      const customer = document.createElement("p");
      customer.textContent = item.name + " • " + item.phone +
        (item.order_id ? " • Buyurtma №" + item.order_id : "");
      const message = document.createElement("p");
      message.textContent = item.message;
      const replyForm = document.createElement("form");
      const area = document.createElement("textarea");
      area.required = true;
      area.minLength = 2;
      area.maxLength = 2000;
      area.rows = 3;
      area.placeholder = "Mijozga javob yozing";
      area.value = item.reply || "";
      const submit = document.createElement("button");
      submit.type = "submit";
      submit.textContent = "Javobni saqlash";
      const info = document.createElement("p");
      info.setAttribute("role", "status");
      replyForm.addEventListener("submit", async (event) => {
        event.preventDefault();
        submit.disabled = true;
        try {
          await postJSON("/api/admin/complaints/" + item.id + "/reply", {
            reply: area.value.trim(), status: "answered",
          }, adminToken());
          info.textContent = "✅ Javob saqlandi";
        } catch (error) {
          info.textContent = error.message;
        } finally {
          submit.disabled = false;
        }
      });
      replyForm.append(area, submit, info);
      card.append(title, customer, message, replyForm);
      target.append(card);
    }
    byId("admin-login-message").textContent = "";
  } catch (error) {
    target.textContent = error.message;
    byId("admin-workspace").hidden = true;
    byId("admin-login-form").hidden = false;
    sessionStorage.removeItem("ali_admin_token");
    byId("admin-login-message").textContent = "Admin sifatida tizimga kiring.";
  }
}

function startAdmin() {
  if (!byId("admin-login-form")) return;
  byId("admin-login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const status = byId("admin-login-message");
    status.textContent = "Tekshirilmoqda…";
    try {
      const login = await postJSON("/api/auth/login", {
        phone: byId("admin-phone").value.trim(),
        password: byId("admin-password").value,
      });
      byId("admin-password").value = "";
      if (login.role !== "admin") throw new Error("Bu hisob administrator emas");
      sessionStorage.setItem("ali_admin_token", login.access_token);
      await loadAdminComplaints();
    } catch (error) {
      status.textContent = error.message;
    }
  });
  byId("admin-refresh").addEventListener("click", loadAdminComplaints);
  byId("admin-logout").addEventListener("click", () => {
    sessionStorage.removeItem("ali_admin_token");
    byId("admin-workspace").hidden = true;
    byId("admin-login-form").hidden = false;
    byId("admin-login-message").textContent = "Tizimdan chiqdingiz.";
  });
  if (adminToken()) loadAdminComplaints();
}

startAdmin();

if (byId("panel-status")) {
  api("/api" + location.pathname + "/status")
    .then((result) => { byId("panel-status").textContent = result.message; })
    .catch((error) => { byId("panel-status").textContent = error.message; });
}
