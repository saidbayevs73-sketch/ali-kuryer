import { Router } from "express";
import { z } from "zod";
import { getFirebaseAdminAuth } from "./firebase-admin.js";

const wrap=fn=>(req,res,next)=>Promise.resolve(fn(req,res,next)).catch(next);
async function auth(req,res,next){
  try{
    const a=getFirebaseAdminAuth(); if(!a)return res.status(503).json({error:"firebase_admin_not_configured"});
    const h=req.headers.authorization||""; if(!h.startsWith("Bearer "))return res.status(401).json({error:"missing_token"});
    req.identity=await a.verifyIdToken(h.slice(7),true); next();
  }catch{return res.status(401).json({error:"invalid_token"});}
}
const admin=(req,res,next)=>{
  const emails=new Set((process.env.ADMIN_EMAILS||"").split(",").map(x=>x.trim().toLowerCase()).filter(Boolean));
  return req.identity?.role==="admin"||emails.has(String(req.identity?.email||"").toLowerCase())?next():res.status(403).json({error:"admin_only"});
};
async function ticketAccess(pool,id,uid,role){
  const {rows:[t]}=await pool.query("SELECT * FROM support_tickets_v2 WHERE id=$1",[id]);
  if(!t)return null;
  if(role==="admin"||t.sender_uid===uid||t.assigned_uid===uid)return t;
  if(!t.assigned_uid&&t.assigned_role===role&&["courier","kitchen"].includes(role))return t;
  return null;
}
export function createSupportReviewRouter(pool){
 const router=Router();
 router.use((req,res,next)=>pool?next():res.status(503).json({error:"database_not_configured"}));
 router.post("/support/tickets",auth,wrap(async(req,res)=>{
  const role=req.identity.role==="courier"||req.identity.role==="kitchen"?req.identity.role:"customer";
  const v=z.object({orderId:z.string().uuid().optional(),subject:z.string().trim().min(3).max(160),message:z.string().trim().min(1).max(5000)}).safeParse(req.body);
  if(!v.success)return res.status(400).json({error:"invalid_ticket"});
  if(v.data.orderId){
   const p=await pool.query("SELECT id,customer_firebase_uid,courier_id FROM orders WHERE id=$1",[v.data.orderId]);
   if(!p.rows[0])return res.status(404).json({error:"order_not_found"});
   if(role==="customer"&&p.rows[0].customer_firebase_uid!==req.identity.uid)return res.status(403).json({error:"not_order_owner"});
  }
  const {rows:[ticket]}=await pool.query("INSERT INTO support_tickets_v2(order_id,sender_uid,sender_role,subject,message) VALUES($1,$2,$3,$4,$5) RETURNING id,status,subject,message,created_at",[v.data.orderId||null,req.identity.uid,role,v.data.subject,v.data.message]);
  res.status(201).json({ticket});
 }));
 router.get("/support/tickets",auth,wrap(async(req,res)=>{
  const role=req.identity.role==="courier"||req.identity.role==="kitchen"?req.identity.role:"customer";
  const isAdmin=req.identity.role==="admin"||new Set((process.env.ADMIN_EMAILS||"").split(",").map(x=>x.trim().toLowerCase())).has(String(req.identity.email||"").toLowerCase());
  const {rows}=isAdmin
   ?await pool.query("SELECT id,order_id,sender_uid,sender_role,subject,message,status,assigned_role,assigned_uid,created_at,updated_at FROM support_tickets_v2 ORDER BY created_at DESC LIMIT 200")
   :await pool.query("SELECT id,order_id,sender_uid,sender_role,subject,message,status,assigned_role,assigned_uid,created_at,updated_at FROM support_tickets_v2 WHERE sender_uid=$1 OR assigned_uid=$1 OR (assigned_uid IS NULL AND assigned_role=$2) ORDER BY created_at DESC LIMIT 100",[req.identity.uid,role]);
  res.json({tickets:rows});
 }));
 router.get("/support/tickets/:id/messages",auth,wrap(async(req,res)=>{
  const role=req.identity.role==="courier"||req.identity.role==="kitchen"?req.identity.role:"customer";
  const t=await ticketAccess(pool,req.params.id,req.identity.uid,role);if(!t)return res.status(404).json({error:"ticket_not_found"});
  const {rows}=await pool.query("SELECT sender_uid,sender_role,body,created_at FROM support_messages WHERE ticket_id=$1 ORDER BY created_at",[t.id]);
  res.json({messages:rows});
 }));
 router.post("/support/tickets/:id/messages",auth,wrap(async(req,res)=>{
  const v=z.object({body:z.string().trim().min(1).max(5000)}).safeParse(req.body);if(!v.success)return res.status(400).json({error:"invalid_message"});
  const role=req.identity.role==="courier"||req.identity.role==="kitchen"?req.identity.role:"customer";
  const t=await ticketAccess(pool,req.params.id,req.identity.uid,role);if(!t)return res.status(404).json({error:"ticket_not_found"});
  if(["resolved","closed"].includes(t.status))return res.status(409).json({error:"ticket_closed"});
  const {rows:[message]}=await pool.query("INSERT INTO support_messages(ticket_id,sender_uid,sender_role,body) VALUES($1,$2,$3,$4) RETURNING sender_uid,sender_role,body,created_at",[t.id,req.identity.uid,role,v.data.body]);
  await pool.query("UPDATE support_tickets_v2 SET updated_at=now() WHERE id=$1",[t.id]);res.status(201).json({message});
 }));
 router.patch("/admin/support/tickets/:id",auth,admin,wrap(async(req,res)=>{
  const v=z.object({status:z.enum(["new","in_progress","resolved","closed"]).optional(),assignedRole:z.enum(["admin","courier","kitchen"]).nullable().optional(),assignedUid:z.string().nullable().optional()}).refine(x=>Object.keys(x).length>0).safeParse(req.body);
  if(!v.success)return res.status(400).json({error:"invalid_ticket_update"});
  const {rows:[t]}=await pool.query("UPDATE support_tickets_v2 SET status=COALESCE($1,status),assigned_role=CASE WHEN $2 THEN $3 ELSE assigned_role END,assigned_uid=CASE WHEN $4 THEN $5 ELSE assigned_uid END,updated_at=now() WHERE id=$6 RETURNING id,status,assigned_role,assigned_uid",[v.data.status||null,Object.hasOwn(v.data,"assignedRole"),v.data.assignedRole??null,Object.hasOwn(v.data,"assignedUid"),v.data.assignedUid??null,req.params.id]);
  if(!t)return res.status(404).json({error:"ticket_not_found"});res.json({ticket:t});
 }));
 router.post("/reviews",auth,wrap(async(req,res)=>{
  const v=z.object({orderId:z.string().uuid(),courierRating:z.number().int().min(1).max(5).nullable().optional(),foodRating:z.number().int().min(1).max(5).nullable().optional(),courierComment:z.string().max(2000).default(""),foodComment:z.string().max(2000).default("")}).refine(x=>x.courierRating!=null||x.foodRating!=null).safeParse(req.body);
  if(!v.success)return res.status(400).json({error:"invalid_review"});
  const {rows:[o]}=await pool.query("SELECT id,customer_firebase_uid,courier_id,kitchen_id,status FROM orders WHERE id=$1",[v.data.orderId]);
  if(!o||o.customer_firebase_uid!==req.identity.uid)return res.status(404).json({error:"order_not_found"});
  if(o.status!=="delivered")return res.status(409).json({error:"order_not_delivered"});
  const {rows:[link]}=o.courier_id?await pool.query("SELECT firebase_uid FROM courier_staff_links WHERE courier_id=$1",[o.courier_id]):{rows:[null]};
  const {rows:[review]}=await pool.query("INSERT INTO private_reviews(order_id,customer_uid,courier_uid,kitchen_id,courier_rating,food_rating,courier_comment,food_comment) VALUES($1,$2,$3,$4,$5,$6,$7,$8) ON CONFLICT(order_id) DO NOTHING RETURNING id,created_at",[o.id,req.identity.uid,link?.firebase_uid||null,o.kitchen_id,v.data.courierRating??null,v.data.foodRating??null,v.data.courierComment,v.data.foodComment]);
  if(!review)return res.status(409).json({error:"review_already_exists"});res.status(201).json({review});
 }));
 router.get("/reviews/:id",auth,wrap(async(req,res)=>{
  const uid=req.identity.uid;
  const {rows:[r]}=await pool.query(`SELECT r.* FROM private_reviews r LEFT JOIN kitchens k ON k.id=r.kitchen_id
   WHERE r.id=$1 AND (r.customer_uid=$2 OR k.owner_uid=$2 OR $3::boolean)`,[req.params.id,uid,req.identity.role==="admin"||new Set((process.env.ADMIN_EMAILS||"").split(",").map(x=>x.trim().toLowerCase())).has(String(req.identity.email||"").toLowerCase())]);
  if(!r)return res.status(404).json({error:"review_not_found"});res.json({review:r});
 }));
 router.get("/admin/reviews",auth,admin,wrap(async(req,res)=>{
  const {rows}=await pool.query("SELECT id,order_id,customer_uid,kitchen_id,courier_rating,food_rating,courier_comment,food_comment,created_at FROM private_reviews ORDER BY created_at DESC LIMIT 200");
  res.json({reviews:rows});
 }));
 return router;
}
