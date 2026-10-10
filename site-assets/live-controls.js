/* Public Ali Kuryer storefront controls. No secret or admin token is sent. */
(() => {
  "use strict";
  const api = "https://ali-kuryer.onrender.com/api/control-center/public";
  async function loadControls() {
    const response = await fetch(api, {cache: "no-store"});
    if (!response.ok) return;
    const data = await response.json();
    const site = data?.settings?.site || {};
    const color = site.site_accent;
    if (typeof color === "string" && /^#[0-9a-fA-F]{6}$/.test(color)) {
      // Strict hexadecimal palette: admins cannot inject arbitrary CSS.
      const style = document.createElement("style");
      style.textContent = "body.marketplace{--red:" + color + ";}" +
        ".marketplace .btn-red,.marketplace .auth-submit,.marketplace .partner-action button{" +
        "background:" + color + "!important;}" +
        ".marketplace .category-chip.active{border-color:" + color + "!important;}";
      document.head.append(style);
    }
    const notice = site.site_notice;
    if (typeof notice === "string" && notice.trim()) {
      const banner = document.createElement("div");
      banner.className = "ali-live-notice";
      banner.setAttribute("role", "status");
      banner.textContent = notice.slice(0, 250); // Never parse admin copy as HTML.
      Object.assign(banner.style, {
        padding: "12px 18px", background: "#fff4eb", color: "#272b33",
        textAlign: "center", fontWeight: "650", borderBottom: "1px solid #efd4c7",
        lineHeight: "1.5"
      });
      const header = document.querySelector("header");
      if (header) header.insertAdjacentElement("afterend", banner);
    }
  }
  loadControls().catch(() => {
    // Safe fallback: original storefront remains usable if config API is offline.
  });
})();
