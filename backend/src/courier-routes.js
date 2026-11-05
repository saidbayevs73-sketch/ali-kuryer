import {Router} from "express";
import {z} from "zod";
import {getFirebaseAdminAuth} from "./firebase-admin.js";
const wrap=fn=>(req,res,next)=>Promise.resolve(fn(req,res,next)).catch(next);
async function auth(req,res,next){try{const a=getFirebaseAdminAuth();if(!a)return res.status(503).json({error:"firebase_admin_not_configured"});const h=req.headers.authorization||"";if(!h.startsWith("Bearer "))return res.status(401).json({error:"missing_token"});req.identity=await a.verifyIdToken(h.slice(7),true);next();}catch{return res.status(401).json({error:"invalid_token"});}}
const courier=(req,res,next)=>req.identity?.role==="courier"&&req.identity?.active!==false?next():res.status(403).json({error:"courier_only"});
const admin=(req,res,next)=>{const e=String(req.identity?.email||"").toLowerCase();const a=new Set((process.env.ADMIN_EMAILS||"").split(",").map(x=>x.trim().toLowerCase()));return req.identity?.role==="admin"||a.has(e)?next():res.status(403).json({error:"admin_only"});};
export function createCourierRouter(pool){
 const router=Router();
 router.use((req,res,next)=>pool?next():res.status(503).json({error:"database_not_configured"}));
 router.post("/admin/couriers/link",auth,admin,wrap(async(req,res)=>{
  const v=z.object({uid:z.string().min(1),phone:z.string().min(7).max(30),fullName:z.string().min(2).max(120)}).safeParse(req.body);
  if(!v.success)return res.status(400).json({error:"invalid_link"});
  const {rows:[courier]}=await pool.query("INSERT INTO couriers(full_name,phone,active) VALUES($1,$2,true) ON CONFLICT(phone) DO UPDATE SET full_name=EXCLUDED.full_name,active=true RETURNING id",[v.data.fullName,v.data.phone]);
  await pool.query("INSERT INTO courier_staff_links(firebase_uid,courier_id) VALUES($1,$2) ON CONFLICT(firebase_uid) DO UPDATE SET courier_id=EXCLUDED.courier_id",[v.data.uid,courier.id]);
  res.json({ok:true});
 }));
 router.post("/courier/orders/:id/accept",auth,courier,wrap(async(req,res)=>{
  const client=await pool.connect();
  try{
   await client.query("BEGIN");
   const {rows:[offer]}=await client.query("SELECT id,order_id FROM courier_dispatch_offers WHERE order_id=$1 AND courier_uid=$2 AND status='offered' AND expires_at>now() FOR UPDATE",[req.params.id,req.identity.uid]);
   if(!offer){await client.query("ROLLBACK");return res.status(409).json({error:"offer_expired_or_unavailable",message:"Taklif muddati tugagan yoki buyurtma boshqa kuryerga berilgan."});}
   await client.query("UPDATE courier_dispatch_offers SET status='accepted',responded_at=now() WHERE id=$1",[offer.id]);
   await client.query("INSERT INTO order_status_history(order_id,old_status,new_status,changed_by_role,note) VALUES($1,'ready','assigned','courier','Kuryer buyurtmani qabul qildi')",[offer.order_id]);
   await client.query("COMMIT");
   res.json({ok:true,message:"Buyurtma qabul qilindi."});
  }catch(error){await client.query("ROLLBACK");throw error;}finally{client.release();}
 }));
 router.post("/courier/orders/:id/decline",auth,courier,wrap(async(req,res)=>{
  const client=await pool.connect();
  try{
   await client.query("BEGIN");
   const {rows:[offer]}=await client.query("SELECT id,order_id,courier_id FROM courier_dispatch_offers WHERE order_id=$1 AND courier_uid=$2 AND status='offered' AND expires_at>now() FOR UPDATE",[req.params.id,req.identity.uid]);
   if(!offer){await client.query("ROLLBACK");return res.status(409).json({error:"offer_expired_or_unavailable"});}
   await client.query("UPDATE courier_dispatch_offers SET status='declined',responded_at=now() WHERE id=$1",[offer.id]);
   await client.query("UPDATE orders SET status='ready',courier_id=NULL,updated_at=now() WHERE id=$1 AND status='assigned' AND courier_id=$2",[offer.order_id,offer.courier_id]);
   await client.query("COMMIT");
   res.json({ok:true,message:"Buyurtma navbatdagi kuryerga yuboriladi."});
  }catch(error){await client.query("ROLLBACK");throw error;}finally{client.release();}
 }));
 router.get("/courier/orders/mine",auth,courier,wrap(async(req,res)=>{
  const {rows}=await pool.query("SELECT o.id,o.public_code,o.delivery_address,o.status,o.total_uzs,o.created_at,COALESCE(d.status='accepted',false) AS offer_accepted FROM orders o JOIN courier_staff_links l ON l.courier_id=o.courier_id LEFT JOIN LATERAL (SELECT status FROM courier_dispatch_offers WHERE order_id=o.id AND courier_uid=$1 ORDER BY offered_at DESC LIMIT 1) d ON true WHERE l.firebase_uid=$1 AND o.status=ANY($2::text[]) ORDER BY o.created_at DESC",[req.identity.uid,["assigned","picked_up","on_the_way"]]);
  res.json({orders:rows});
 }));
 router.patch("/courier/orders/:id/status",auth,courier,wrap(async(req,res)=>{
  const v=z.enum(["picked_up","on_the_way","delivered"]).safeParse(req.body.status);
  if(!v.success)return res.status(400).json({error:"invalid_status"});
  const prev={picked_up:["assigned"],on_the_way:["picked_up"],delivered:["on_the_way"]};
  const {rows}=await pool.query("UPDATE orders SET status=$1,delivered_at=CASE WHEN $1='delivered' THEN now() ELSE delivered_at END,contact_closed_at=CASE WHEN $1='delivered' THEN now() ELSE contact_closed_at END,updated_at=now() WHERE id=$2 AND courier_id=(SELECT courier_id FROM courier_staff_links WHERE firebase_uid=$3) AND status=ANY($4::text[]) AND ($1<>'picked_up' OR EXISTS(SELECT 1 FROM courier_dispatch_offers d WHERE d.order_id=orders.id AND d.courier_uid=$3 AND d.status='accepted')) RETURNING id,public_code,status",[v.data,req.params.id,req.identity.uid,prev[v.data]]);
  if(!rows[0])return res.status(409).json({error:"invalid_order_transition"});
  res.json({order:rows[0]});
 }));
 router.post("/courier/presence",auth,courier,wrap(async(req,res)=>{
  const v=z.object({online:z.boolean(),latitude:z.number().min(-90).max(90),longitude:z.number().min(-180).max(180),accuracy:z.number().min(0).max(10000).optional()}).safeParse(req.body);
  if(!v.success)return res.status(400).json({error:"invalid_location"});
  const link=await pool.query("SELECT courier_id FROM courier_staff_links WHERE firebase_uid=$1",[req.identity.uid]);
  if(!link.rows[0])return res.status(409).json({error:"courier_profile_not_linked"});
  const x=v.data;
  await pool.query("INSERT INTO courier_presence(courier_uid,is_online,latitude,longitude,accuracy_m,updated_at) VALUES($1,$2,$3,$4,$5,now()) ON CONFLICT(courier_uid) DO UPDATE SET is_online=EXCLUDED.is_online,latitude=EXCLUDED.latitude,longitude=EXCLUDED.longitude,accuracy_m=EXCLUDED.accuracy_m,updated_at=now()",[req.identity.uid,x.online,x.latitude,x.longitude,x.accuracy??null]);
  res.json({ok:true});
 }));
 return router;
}
