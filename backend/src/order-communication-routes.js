import { Router } from "express";
import { z } from "zod";
import { getFirebaseAdminAuth } from "./firebase-admin.js";

const wrap = fn => (req,res,next) => Promise.resolve(fn(req,res,next)).catch(next);
async function signedIn(req,res,next) {
  try {
    const auth = getFirebaseAdminAuth();
    if (!auth) return res.status(503).json({error:"firebase_admin_not_configured"});
    const h = req.headers.authorization || "";
    if (!h.startsWith("Bearer ")) return res.status(401).json({error:"missing_token"});
    req.identity = await auth.verifyIdToken(h.slice(7), true);
    next();
  } catch { return res.status(401).json({error:"invalid_token"}); }
}
async function participant(pool, orderId, uid) {
  const {rows:[o]} = await pool.query(
    `SELECT o.id,o.customer_firebase_uid,o.status,o.contact_closed_at,l.firebase_uid AS courier_uid
       FROM orders o LEFT JOIN courier_staff_links l ON l.courier_id=o.courier_id
      WHERE o.id=$1`, [orderId]);
  if (!o) return null;
  if (o.customer_firebase_uid === uid) return {...o, role:"customer", peer:o.courier_uid};
  if (o.courier_uid === uid) return {...o, role:"courier", peer:o.customer_firebase_uid};
  return null;
}
const isActive = o => ["assigned","picked_up","on_the_way"].includes(o.status) && !o.contact_closed_at;

export function createOrderCommunicationRouter(pool) {
  const router = Router();
  router.use((req,res,next)=>pool?next():res.status(503).json({error:"database_not_configured"}));

  router.get("/orders/:id/chat", signedIn, wrap(async(req,res)=>{
    const p=await participant(pool,req.params.id,req.identity.uid);
    if(!p)return res.status(404).json({error:"order_not_found"});
    if(!isActive(p))return res.status(403).json({error:"contact_closed"});
    const {rows}=await pool.query(
      "SELECT id,sender_uid,sender_role,body,created_at FROM order_chat_messages WHERE order_id=$1 ORDER BY created_at DESC LIMIT 100",
      [p.id]);
    res.json({messages:rows.reverse()});
  }));

  router.post("/orders/:id/chat", signedIn, wrap(async(req,res)=>{
    const parsed=z.object({body:z.string().trim().min(1).max(4000)}).safeParse(req.body);
    if(!parsed.success)return res.status(400).json({error:"invalid_message"});
    const p=await participant(pool,req.params.id,req.identity.uid);
    if(!p)return res.status(404).json({error:"order_not_found"});
    if(!isActive(p))return res.status(403).json({error:"contact_closed"});
    const {rows:[message]}=await pool.query(
      "INSERT INTO order_chat_messages(order_id,sender_uid,sender_role,body) VALUES($1,$2,$3,$4) RETURNING id,sender_uid,sender_role,body,created_at",
      [p.id,req.identity.uid,p.role,parsed.data.body]);
    res.status(201).json({message});
  }));

  router.post("/orders/:id/calls", signedIn, wrap(async(req,res)=>{
    const p=await participant(pool,req.params.id,req.identity.uid);
    if(!p)return res.status(404).json({error:"order_not_found"});
    if(!isActive(p)||!p.peer)return res.status(403).json({error:"contact_closed_or_peer_missing"});
    const existing=await pool.query("SELECT id FROM order_call_sessions WHERE order_id=$1 AND status IN ('ringing','accepted') LIMIT 1",[p.id]);
    if(existing.rows[0])return res.status(409).json({error:"call_already_active",callId:existing.rows[0].id});
    const {rows:[call]}=await pool.query(
      "INSERT INTO order_call_sessions(order_id,caller_uid,callee_uid,call_type) VALUES($1,$2,$3,'audio') RETURNING id,caller_uid,callee_uid,status,created_at",
      [p.id,req.identity.uid,p.peer]);
    res.status(201).json({call});
  }));

  router.get("/orders/:id/calls/current", signedIn, wrap(async(req,res)=>{
    const p=await participant(pool,req.params.id,req.identity.uid);
    if(!p||!isActive(p))return res.status(404).json({error:"call_not_found"});
    const {rows:[call]}=await pool.query(
      "SELECT id,caller_uid,callee_uid,status,created_at,ended_at FROM order_call_sessions WHERE order_id=$1 AND (caller_uid=$2 OR callee_uid=$2) AND status IN ('ringing','accepted') ORDER BY created_at DESC LIMIT 1",
      [p.id,req.identity.uid]);
    if(!call)return res.json({call:null,signals:[]});
    const {rows:signals}=await pool.query(
      "SELECT id,sender_uid,signal_type,payload,created_at FROM order_call_signals WHERE call_id=$1 AND sender_uid<>$2 ORDER BY created_at",
      [call.id,req.identity.uid]);
    res.json({call,signals});
  }));

  router.get("/orders/:id/calls/:callId", signedIn, wrap(async(req,res)=>{
    const p=await participant(pool,req.params.id,req.identity.uid);
    if(!p||!isActive(p))return res.status(404).json({error:"call_not_found"});
    const {rows:[call]}=await pool.query(
      "SELECT id,caller_uid,callee_uid,status,created_at,ended_at FROM order_call_sessions WHERE id=$1 AND order_id=$2 AND (caller_uid=$3 OR callee_uid=$3)",
      [req.params.callId,p.id,req.identity.uid]);
    if(!call)return res.status(404).json({error:"call_not_found"});
    const {rows:signals}=await pool.query(
      "SELECT id,sender_uid,signal_type,payload,created_at FROM order_call_signals WHERE call_id=$1 AND sender_uid<>$2 ORDER BY created_at",
      [call.id,req.identity.uid]);
    res.json({call,signals});
  }));

  router.post("/orders/:id/calls/:callId/signals", signedIn, wrap(async(req,res)=>{
    const parsed=z.object({signalType:z.enum(["offer","answer","ice","hangup"]),payload:z.record(z.any()).default({})}).safeParse(req.body);
    if(!parsed.success)return res.status(400).json({error:"invalid_signal"});
    const p=await participant(pool,req.params.id,req.identity.uid);
    if(!p||!isActive(p))return res.status(403).json({error:"contact_closed"});
    const {rows:[call]}=await pool.query(
      "SELECT id,status FROM order_call_sessions WHERE id=$1 AND order_id=$2 AND (caller_uid=$3 OR callee_uid=$3)",
      [req.params.callId,p.id,req.identity.uid]);
    if(!call||!["ringing","accepted"].includes(call.status))return res.status(404).json({error:"call_not_active"});
    const payload=JSON.stringify(parsed.data.payload);
    const {rows:[signal]}=await pool.query(
      "INSERT INTO order_call_signals(call_id,sender_uid,signal_type,payload) VALUES($1,$2,$3,$4::jsonb) RETURNING id",
      [call.id,req.identity.uid,parsed.data.signalType,payload]);
    if(parsed.data.signalType==="hangup")await pool.query("UPDATE order_call_sessions SET status='ended',ended_at=now() WHERE id=$1",[call.id]);
    res.status(201).json({signalId:signal.id});
  }));

  router.patch("/orders/:id/calls/:callId", signedIn, wrap(async(req,res)=>{
    const parsed=z.object({status:z.enum(["accepted","rejected","ended"])}).safeParse(req.body);
    if(!parsed.success)return res.status(400).json({error:"invalid_call_status"});
    const p=await participant(pool,req.params.id,req.identity.uid);
    if(!p||!isActive(p))return res.status(403).json({error:"contact_closed"});
    const {rows:[call]}=await pool.query(
      "UPDATE order_call_sessions SET status=$1,ended_at=CASE WHEN $1 IN ('rejected','ended') THEN now() ELSE ended_at END WHERE id=$2 AND order_id=$3 AND callee_uid=$4 AND status='ringing' RETURNING id,status",
      [parsed.data.status,req.params.callId,p.id,req.identity.uid]);
    if(!call)return res.status(409).json({error:"call_transition_denied"});
    res.json({call});
  }));
  return router;
}
