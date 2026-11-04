import { cert, getApps, initializeApp } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";

let cachedAuth = null;

export function getFirebaseAdminAuth() {
  if (cachedAuth) return cachedAuth;
  if (getApps().length) {
    cachedAuth = getAuth();
    return cachedAuth;
  }
  const raw = process.env.FIREBASE_SERVICE_ACCOUNT_JSON;
  if (!raw) return null;
  let serviceAccount;
  try {
    serviceAccount = JSON.parse(raw);
  } catch {
    throw new Error("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON");
  }
  const app = initializeApp({ credential: cert(serviceAccount) });
  cachedAuth = getAuth(app);
  return cachedAuth;
}
