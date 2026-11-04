import { Router } from "express";
import { z } from "zod";
import { getFirebaseAdminAuth } from "./firebase-admin.js";

const router = Router();
const wrap = fn => (req,res,next) => Promise.resolve(fn(req,res,next)).catch(next);

async function signedIn(req,res,next) {
  try {
    const auth = getFirebaseAdminAuth();
    if (!auth) return res.status(503).json({error:"firebase_admin_not_configured"});
    const header = req.headers.authorization || "";
    if (!header.startsWith("Bearer ")) return res.status(401).json({error:"missing_token"});
    req.identity = await auth.verifyIdToken(header.slice(7), true);
    next();
  } catch { res.status(401).json({error:"invalid_token"}); }
}
const role = name => (req,res,next) => req.identity?.role === name && req.identity?.active !== false ? next() : res.status(403).json({error:"wrong_role"});
const kitchenProfile = async (pool, uid) => {
  const {rows} = await pool.query("SELECT * FROM kitchens WHERE owner_uid=$1 ORDER BY created_at LIMIT 1",[uid]);
  return rows[0] || null;
};

export function createKitchenRouter(pool) {
  router.use((req,res,next) => pool ? next() : res.status(503).json({error:"database_not_configured"}));
  router.get("/kitchen/profile",signedIn,role("kitchen"),wrap(async(req,res)=>{
    res.json({kitchen:await kitchenProfile(pool,req.identity.uid)});
  }));
  router.post("/kitchen/profile",signedIn,role("kitchen"),wrap(async(req,res)=>{
    const schema=z.object({name:z.string().trim().min(2).max(120),description:z.string().max(1000).default(""),phone:z.string().min(7).max(30),address:z.string().min(5).max(500),latitude:z.number().min(-90).max(90).nullable().optional(),longitude:z.number().min(-180).max(180).nullable().optional(),logoUrl:z.string().url().nullable().optional()});
    const parsed=schema.safeParse(req.body);
    if(!parsed.success)return res.status(400).json({error:"invalid_profile",details:parsed.error.flatten()});
    if(await kitchenProfile(pool,req.identity.uid))return res.status(409).json({error:"profile_exists"});
    const v=parsed.data;
    const {rows:[k]}=await pool.query("INSERT INTO kitchens(owner_uid,name,description,phone,address,latitude,longitude,logo_url) VALUES($1,$2,$3,$4,$5,$6,$7,$8) RETURNING id,name,description,phone,address,latitude,longitude,logo_url,active",[req.identity.uid,v.name,v.description,v.phone,v.address,v.latitude??null,v.longitude??null,v.logoUrl??null]);
    res.status(201).json({kitchen:k,notice:"Profil yaratildi; katalogda chiqishi uchun admin tasdig‘i kerak."});
  }));
  router.get("/kitchen/products",signedIn,role("kitchen"),wrap(async(req,res)=>{
    const k=await kitchenProfile(pool,req.identity.uid);
    if(!k)return res.status(409).json({error:"profile_required"});
    const {rows}=await pool.query("SELECT id,name,description,ingredients,price_uzs,image_url,available,photo_source FROM products WHERE kitchen_id=$1 ORDER BY created_at DESC",[k.id]);
    res.json({products:rows});
  }));
  router.post("/kitchen/products",signedIn,role("kitchen"),wrap(async(req,res)=>{
    const schema=z.object({name:z.string().trim().min(2).max(160),description:z.string().max(1000).default(""),ingredients:z.string().max(2000).default(""),price:z.number().int().min(0).max(100000000),imageUrl:z.string().url().nullable().optional(),available:z.boolean().default(true),photoSource:z.enum(["camera","upload"]).default("upload")});
    const parsed=schema.safeParse(req.body);
    if(!parsed.success)return res.status(400).json({error:"invalid_product",details:parsed.error.flatten()});
    const k=await kitchenProfile(pool,req.identity.uid);
    if(!k)return res.status(409).json({error:"profile_required"});
    if(!k.active)return res.status(403).json({error:"kitchen_not_approved"});
    const v=parsed.data;
    const category=await pool.query("INSERT INTO categories(name,slug,sort_order,active) VALUES('Oshxona taomlari','oshxona-taomlari',0,true) ON CONFLICT(name) DO UPDATE SET active=true RETURNING id");
    const {rows:[p]}=await pool.query("INSERT INTO products(kitchen_id,category_id,name,description,ingredients,price_uzs,image_url,available,photo_source) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING id,name,description,ingredients,price_uzs,image_url,available,photo_source",[k.id,category.rows[0].id,v.name,v.description,v.ingredients,v.price,v.imageUrl??null,v.available,v.photoSource]);
    res.status(201).json({product:p});
  }));
  router.get("/kitchen/orders",signedIn,role("kitchen"),wrap(async(req,res)=>{
    const k=await kitchenProfile(pool,req.identity.uid);
    if(!k)return res.status(409).json({error:"profile_required"});
    const {rows}=await pool.query("SELECT id,public_code,customer_name,customer_phone,delivery_address,status,total_uzs,created_at FROM orders WHERE kitchen_id=$1 ORDER BY created_at DESC LIMIT 100",[k.id]);
    res.json({orders:rows});
  }));
  router.patch("/kitchen/orders/:id/status",signedIn,role("kitchen"),wrap(async(req,res)=>{
    const v=z.enum(["accepted","preparing","ready","cancelled"]).safeParse(req.body.status);
    if(!v.success)return res.status(400).json({error:"invalid_status"});
    const k=await kitchenProfile(pool,req.identity.uid);
    if(!k)return res.status(409).json({error:"profile_required"});
    const previous={accepted:["new"],preparing:["accepted"],ready:["preparing"],cancelled:["new","accepted","preparing"]};
    const {rows}=await pool.query("UPDATE orders SET status=$1,accepted_at=CASE WHEN $1='accepted' THEN now() ELSE accepted_at END,updated_at=now() WHERE id=$2 AND kitchen_id=$3 AND status=ANY($4::text[]) RETURNING id,public_code,status",[v.data,req.params.id,k.id,previous[v.data]]);
    if(!rows[0])return res.status(409).json({error:"invalid_order_transition"});
    res.json({order:rows[0]});
  }));
  return router;
}
