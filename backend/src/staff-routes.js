import { Router } from "express";
import rateLimit from "express-rate-limit";
import { z } from "zod";
import { getFirebaseAdminAuth } from "./firebase-admin.js";

const router = Router();
const createStaffLimit = rateLimit({ windowMs: 15 * 60_000, limit: 12, standardHeaders: "draft-7", legacyHeaders: false });
const allowedRoles = new Set(["courier", "kitchen"]);
const adminEmails = new Set((process.env.ADMIN_EMAILS || "").split(",").map(x => x.trim().toLowerCase()).filter(Boolean));

function getAuthOr503(res) {
  const auth = getFirebaseAdminAuth();
  if (!auth) {
    res.status(503).json({ error: "firebase_admin_not_configured", message: "Serverda Firebase Admin xizmati hali sozlanmagan." });
    return null;
  }
  return auth;
}

async function requireUser(req, res, next) {
  try {
    const auth = getAuthOr503(res);
    if (!auth) return;
    const header = req.headers.authorization || "";
    const token = header.startsWith("Bearer ") ? header.slice(7) : "";
    if (!token) return res.status(401).json({ error: "missing_token", message: "Avval tizimga kiring." });
    req.authUser = await auth.verifyIdToken(token, true);
    req.adminAuth = auth;
    next();
  } catch (error) {
    if (res.headersSent) return;
    res.status(401).json({ error: "invalid_token", message: "Kirish muddati tugagan. Qayta kiring." });
  }
}

function requireAdmin(req, res, next) {
  const email = String(req.authUser?.email || "").toLowerCase();
  if (req.authUser?.role === "admin" || adminEmails.has(email)) return next();
  return res.status(403).json({ error: "admin_only", message: "Bu bo‘lim faqat administrator uchun." });
}

const staffSchema = z.object({
  email: z.string().trim().email().max(254),
  password: z.string().min(10).max(128),
  displayName: z.string().trim().min(2).max(100),
  role: z.enum(["courier", "kitchen"])
});

router.get("/staff/me", requireUser, async (req, res) => {
  const role = req.authUser.role;
  if (!allowedRoles.has(role) || req.authUser.active === false) {
    return res.status(403).json({ error: "staff_role_required", message: "Bu hisob kuryer yoki oshxona xodimi sifatida faollashtirilmagan." });
  }
  const user = await req.adminAuth.getUser(req.authUser.uid);
  if (user.disabled) return res.status(403).json({ error: "account_disabled", message: "Hisob administrator tomonidan vaqtincha bloklangan." });
  res.json({ uid: user.uid, email: user.email, displayName: user.displayName || "", role, active: true });
});

router.get("/admin/staff", requireUser, requireAdmin, async (req, res) => {
  const users = [];
  let pageToken;
  do {
    const page = await req.adminAuth.listUsers(1000, pageToken);
    users.push(...page.users.filter(user => allowedRoles.has(user.customClaims?.role)));
    pageToken = page.pageToken;
  } while (pageToken);
  res.json({ staff: users.map(user => ({
    uid: user.uid, email: user.email || "", displayName: user.displayName || "",
    role: user.customClaims.role, disabled: Boolean(user.disabled),
    createdAt: user.metadata.creationTime || null, lastSignInAt: user.metadata.lastSignInTime || null
  })) });
});

router.post("/admin/staff", requireUser, requireAdmin, createStaffLimit, async (req, res) => {
  const parsed = staffSchema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: "invalid_staff", details: parsed.error.flatten() });
  const { email, password, displayName, role } = parsed.data;
  try {
    const user = await req.adminAuth.createUser({ email, password, displayName, disabled: false, emailVerified: false });
    try {
      await req.adminAuth.setCustomUserClaims(user.uid, { role, active: true });
    } catch (error) {
      await req.adminAuth.deleteUser(user.uid);
      throw error;
    }
    res.status(201).json({ staff: { uid: user.uid, email: user.email, displayName: user.displayName, role, disabled: false } });
  } catch (error) {
    if (error.code === "auth/email-already-exists") return res.status(409).json({ error: "email_exists", message: "Bu login/email oldin ro‘yxatdan o‘tgan." });
    throw error;
  }
});

router.patch("/admin/staff/:uid", requireUser, requireAdmin, async (req, res) => {
  const parsed = z.object({ disabled: z.boolean() }).safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: "invalid_status", message: "Bloklash holati noto‘g‘ri." });
  if (req.params.uid === req.authUser.uid) return res.status(400).json({ error: "cannot_change_self", message: "O‘z administrator hisobingizni bu yerdan bloklay olmaysiz." });
  const user = await req.adminAuth.getUser(req.params.uid);
  if (!allowedRoles.has(user.customClaims?.role)) return res.status(404).json({ error: "staff_not_found" });
  await req.adminAuth.updateUser(user.uid, { disabled: parsed.data.disabled });
  await req.adminAuth.setCustomUserClaims(user.uid, { ...user.customClaims, active: !parsed.data.disabled });
  res.json({ uid: user.uid, disabled: parsed.data.disabled, role: user.customClaims.role });
});

export function createStaffRouter() {
  return router;
}
