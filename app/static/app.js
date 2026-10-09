"use strict";
async function readApi(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error("Ma’lumotni olish imkoni bo‘lmadi");
  return response.json();
}
async function showMenu(restaurant) {
  const section = document.getElementById("menu");
  section.replaceChildren();
  try {
    const data = await readApi(`/api/customer/restaurants/${restaurant.id}/menu`);
    const title = document.createElement("h2");
    title.textContent = restaurant.name;
    const list = document.createElement("ul");
    for (const item of data.items) {
      const row = document.createElement("li");
      row.textContent = `${item.name} — ${new Intl.NumberFormat("uz-UZ").format(item.price)} so‘m`;
      list.append(row);
    }
    section.append(title, list);
    if (!data.items.length) section.append("Menyu hozircha bo‘sh.");
  } catch (error) { section.textContent = error.message; }
}
async function start() {
  const restaurants = document.getElementById("restaurants");
  if (restaurants) {
    const message = document.getElementById("message");
    try {
      const data = await readApi("/api/customer/restaurants");
      message.textContent = data.length ? "" : "Oshxonalar hozircha mavjud emas.";
      for (const restaurant of data) {
        const button = document.createElement("button");
        button.textContent = restaurant.name;
        button.addEventListener("click", () => showMenu(restaurant));
        restaurants.append(button);
      }
    } catch (error) { message.textContent = error.message; }
  }
  const status = document.getElementById("panel-status");
  if (status) {
    try { status.textContent = (await readApi(`/api${location.pathname}/status`)).message; }
    catch (error) { status.textContent = error.message; }
  }
}
start();
