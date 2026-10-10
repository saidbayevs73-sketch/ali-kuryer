"use strict";
// The token is intentionally held in memory only: never in a URL, cookie,
// localStorage, sessionStorage, or an analytics event.
let accessToken = "";
let activeTab = "overview";
const cache = {orders: [], restaurants: [], partners: [], support: []};
const $ = id => document.getElementById(id);
const show = (element, yes) => element.classList.toggle("hidden", !yes);
function message(id, value) {
  const node = $(id);
  node.textContent = value || "";
  show(node, !!value);
}
function logout(note = "") {
  accessToken = "";
  $("password").value = "";
  $("current-pass").value = "";
  $("new-pass").value = "";
  $("repeat-pass").value = "";
  show($("admin-app"), false);
  show($("login-screen"), true);
  message("login-message", note);
}
async function api(path, options = {}) {
  const headers = {"Accept": "application/json", ...(options.body ? {"Content-Type": "application/json"} : {})};
  if (accessToken) headers.Authorization = "Bearer " + accessToken;
  let res;
  try { res = await fetch(path, {...options, headers, credentials: "same-origin", cache: "no-store"}); }
  catch { throw Error("Server bilan aloqa yo‘q. Internetni tekshiring."); }
  let body = {};
  try { body = await res.json(); } catch {}
  if (!res.ok) {
    if (res.status === 401 && accessToken) { logout("Sessiya yakunlandi. Qayta kiring."); throw Error("Sessiya yakunlandi."); }
    throw Error(typeof body.detail === "string" ? body.detail : "Server xatosi: " + res.status);
  }
  return body;
}
function listOf(v) { return Array.isArray(v) ? v : []; }
function item(container, title, desc, badge = "") {
  const node = document.createElement("div"); node.className = "item";
  const copy = document.createElement("div");
  const bold = document.createElement("b"); bold.textContent = title;
  const small = document.createElement("small"); small.textContent = desc;
  copy.append(bold, small); node.append(copy);
  if (badge) { const pill = document.createElement("span"); pill.className = "pill"; pill.textContent = badge; node.append(pill); }
  container.append(node);
  return node;
}
function render(target, rows, renderOne) {
  const el = $(target); el.replaceChildren();
  if (!rows.length) { const n = document.createElement("p"); n.className = "empty"; n.textContent = "Hozircha ma’lumot yo‘q."; el.append(n); return; }
  rows.forEach(row => renderOne(el, row));
}
function orderRow(el, x) {
  const o = x.order && typeof x.order === "object" ? x.order : x;
  item(el, "Buyurtma №" + (o.id ?? "—"), String(o.customer_name || o.status || "Buyurtma") + " · " + (o.total ?? "—") + " so‘m", String(o.status || "Jarayonda"));
}
function restaurantRow(el, x) {
  const node = item(el, String(x.name || "Oshxona"), "ID: " + (x.id ?? "—"), x.is_approved === false ? "Tasdiqlanmagan" : "Ro‘yxatda");
  if (x.is_approved === false && Number.isInteger(x.id) && x.id > 0) {
    const button = document.createElement("button");
    button.type = "button"; button.className = "btn secondary";
    button.textContent = "Tasdiqlash";
    button.addEventListener("click", async () => {
      if (!window.confirm("Ushbu oshxonani Ali Kuryer tizimiga tasdiqlaysizmi?")) return;
      button.disabled = true;
      try {
        await api("/api/v1/admin/restaurants/" + encodeURIComponent(String(x.id)) + "/approval",
          {method: "POST", body: JSON.stringify({approved: true})});
        await refresh();
      } catch (err) {
        message("content-message", err.message || "Oshxonani tasdiqlashda xato");
        button.disabled = false;
      }
    });
    node.append(button);
  }
}
function partnerRow(el, x) {
  item(el, String(x.name || x.full_name || "Hamkor"), String(x.phone || "Aloqa ma’lumoti yo‘q"), String(x.kind || x.status || "Ariza"));
}
function supportRow(el, x) {
  item(el, "Mijoz №" + (x.customer_id ?? "—"), String(x.last_message || "Yordam suhbati"), String(x.unread_count || 0) + " yangi");
}
async function refresh() {
  if (!accessToken) return;
  message("content-message", "");
  const endpoints = {
    orders: "/api/v1/staff/orders",
    restaurants: "/api/v1/staff/restaurants",
    partners: "/api/admin/partner-applications",
    support: "/api/v1/admin/support/threads"
  };
  const results = await Promise.allSettled(Object.entries(endpoints).map(async ([key, path]) => [key, await api(path)]));
  let errors = [];
  const failed = new Set();
  for (let index = 0; index < results.length; index++) {
    const entry = results[index];
    const key = Object.keys(endpoints)[index];
    if (entry.status === "fulfilled") cache[key] = listOf(entry.value[1]);
    else {cache[key] = []; failed.add(key); errors.push(key + ": " + (entry.reason.message || "xato"));}
  }
  for (const key of ["orders", "restaurants", "partners", "support"]) {
    const node = $("stat-" + (key === "support" ? "threads" : key));
    node.textContent = failed.has(key) ? "—" : String(cache[key].length);
  }
  render("recent-orders", cache.orders.slice(0,5), orderRow);
  render("recent-partners", cache.partners.slice(0,5), partnerRow);
  render("order-list", cache.orders, orderRow);
  render("restaurant-list", cache.restaurants, restaurantRow);
  render("partner-list", cache.partners, partnerRow);
  render("support-list", cache.support, supportRow);
  const displays = {orders:["recent-orders","order-list"], partners:["recent-partners","partner-list"],
                    restaurants:["restaurant-list"],support:["support-list"]};
  for (const key of failed) for (const target of displays[key]) {
    const element = $(target);
    element.replaceChildren();
    const notice = document.createElement("p");
    notice.className = "empty danger";
    notice.textContent = "Serverdan ma’lumot olinmadi. Qayta urinib ko‘ring.";
    element.append(notice);
  }
  if (errors.length) message("content-message", "Ba’zi ma’lumotlarni olishning iloji bo‘lmadi: " + errors.join("; "));
}
function tab(name) {
  activeTab = name;
  document.querySelectorAll("[data-page]").forEach(el => show(el, el.id === name));
  document.querySelectorAll("[data-tab]").forEach(el => el.classList.toggle("active", el.dataset.tab === name));
  const titles = {overview:"Umumiy nazorat",orders:"Buyurtmalar",restaurants:"Oshxonalar",partners:"Hamkorlik arizalari",support:"Operator suhbatlari",security:"Xavfsizlik"};
  $("page-title").textContent = titles[name] || "Boshqaruv";
}
document.querySelectorAll("[data-tab]").forEach(el => el.addEventListener("click", () => tab(el.dataset.tab)));
$("refresh").addEventListener("click", () => {refresh().catch(e => message("content-message", e.message));});
$("logout").addEventListener("click", () => logout());
$("login-form").addEventListener("submit", async e => {
  e.preventDefault();
  $("login-button").disabled = true;
  message("login-message", "");
  try {
    const data = await api("/api/auth/admin/login", {
      method: "POST",
      body: JSON.stringify({username: $("username").value.trim(), password: $("password").value})
    });
    if (data.role !== "admin" || !data.access_token) throw Error("Admin ruxsati tasdiqlanmadi.");
    accessToken = data.access_token;
    $("password").value = "";
    show($("login-screen"), false); show($("admin-app"), true);
    tab("overview");
    await refresh();
  } catch (err) { message(accessToken ? "content-message" : "login-message", err.message); }
  finally { $("login-button").disabled = false; }
});
$("password-form").addEventListener("submit", async e => {
  e.preventDefault();
  message("password-message", "");
  const next = $("new-pass").value;
  if (next !== $("repeat-pass").value) {message("password-message", "Parollar bir xil emas."); return;}
  if (next.length < 14) {message("password-message", "Kamida 14 belgili kuchli parol kiriting."); return;}
  try {
    await api("/api/auth/admin/change-password", {
      method: "POST", body: JSON.stringify({current_password: $("current-pass").value, new_password: next})
    });
    logout("Admin paroli o‘zgartirildi. Yangi parol bilan kiring.");
  } catch (err) {message("password-message", err.message);}
});
