// Automatic nearest-courier dispatch worker. Requires migration 005.
const wrapTx = async (pool, work) => {
  const client = await pool.connect();
  try { await client.query("BEGIN"); const value = await work(client); await client.query("COMMIT"); return value; }
  catch (error) { await client.query("ROLLBACK"); throw error; }
  finally { client.release(); }
};

async function expireOffers(pool) {
  return wrapTx(pool, async client => {
    const { rows } = await client.query(`
      SELECT id,order_id,courier_id FROM courier_dispatch_offers
       WHERE status='offered' AND expires_at<=now()
       ORDER BY expires_at LIMIT 25 FOR UPDATE SKIP LOCKED
    `);
    for (const offer of rows) {
      await client.query("UPDATE courier_dispatch_offers SET status='expired' WHERE id=$1 AND status='offered'", [offer.id]);
      await client.query("UPDATE orders SET status='ready',courier_id=NULL,updated_at=now() WHERE id=$1 AND status='assigned' AND courier_id=$2", [offer.order_id,offer.courier_id]);
    }
    return rows.length;
  });
}

async function offerNextCourier(pool) {
  return wrapTx(pool, async client => {
    const { rows: orders } = await client.query(`
      SELECT o.id,o.latitude,o.longitude,o.public_code
        FROM orders o
       WHERE o.status='ready'
         AND NOT EXISTS (SELECT 1 FROM courier_dispatch_offers d WHERE d.order_id=o.id AND d.status='offered')
         AND NOT EXISTS (SELECT 1 FROM dispatch_queue_alerts a WHERE a.order_id=o.id AND a.cleared_at IS NULL AND a.alerted_at>now()-interval '30 seconds')
       ORDER BY o.created_at
       LIMIT 1 FOR UPDATE OF o SKIP LOCKED
    `);
    const order=orders[0];
    if (!order) return "none";
    if (order.latitude===null || order.longitude===null) {
      const alert=await client.query("INSERT INTO dispatch_queue_alerts(order_id) VALUES($1) ON CONFLICT(order_id) DO UPDATE SET alerted_at=now(),cleared_at=NULL RETURNING (xmax=0) AS inserted",[order.id]);
      if (alert.rows[0]?.inserted) await client.query("INSERT INTO platform_audit_log(actor_uid,actor_role,action,target_type,target_id,details) VALUES('system','system','dispatch_missing_customer_location','order',$1,$2::jsonb)",[order.id,JSON.stringify({publicCode:order.public_code,message:'Mijoz manzili koordinatasi yo‘q'})]);
      return "waiting";
    }
    const { rows: couriers } = await client.query(`
      SELECT c.id,l.firebase_uid,
        6371*2*ASIN(SQRT(
          POWER(SIN(RADIANS(cp.latitude-$1)/2),2)+
          COS(RADIANS($1))*COS(RADIANS(cp.latitude))*
          POWER(SIN(RADIANS(cp.longitude-$2)/2),2)
        )) AS distance_km
      FROM courier_presence cp
      JOIN courier_staff_links l ON l.firebase_uid=cp.courier_uid
      JOIN couriers c ON c.id=l.courier_id AND c.active=true
      WHERE cp.is_online=true AND cp.latitude IS NOT NULL AND cp.longitude IS NOT NULL
        AND cp.updated_at>now()-interval '90 seconds'
        AND NOT EXISTS (SELECT 1 FROM orders a WHERE a.courier_id=c.id AND a.status IN ('assigned','picked_up','on_the_way'))
        AND NOT EXISTS (SELECT 1 FROM courier_dispatch_offers old
                         WHERE old.order_id=$3 AND old.courier_id=c.id
                           AND old.status IN ('accepted','declined','expired'))
      ORDER BY distance_km ASC
      LIMIT 1 FOR UPDATE OF c SKIP LOCKED
    `,[order.latitude,order.longitude,order.id]);
    const courier=couriers[0];
    if (!courier) {
      const alert=await client.query("INSERT INTO dispatch_queue_alerts(order_id) VALUES($1) ON CONFLICT(order_id) DO UPDATE SET alerted_at=now(),cleared_at=NULL RETURNING (xmax=0) AS inserted",[order.id]);
      if (alert.rows[0]?.inserted) {
        await client.query("INSERT INTO platform_audit_log(actor_uid,actor_role,action,target_type,target_id,details) VALUES('system','system','dispatch_waiting_for_courier','order',$1,$2::jsonb)",[order.id,JSON.stringify({publicCode:order.public_code,message:'Mos onlayn kuryer topilmadi'})]);
      }
      return "waiting";
    }
    await client.query("UPDATE orders SET status='assigned',courier_id=$2,updated_at=now() WHERE id=$1 AND status='ready'",[order.id,courier.id]);
    await client.query("INSERT INTO courier_dispatch_offers(order_id,courier_id,courier_uid) VALUES($1,$2,$3)",[order.id,courier.id,courier.firebase_uid]);
    await client.query("INSERT INTO notifications(courier_id,title,body) VALUES($1,$2,$3)",[courier.id,'Yangi buyurtma',`${order.public_code} buyurtmasini 30 soniya ichida qabul qiling.`]);
    await client.query("UPDATE dispatch_queue_alerts SET cleared_at=now() WHERE order_id=$1 AND cleared_at IS NULL",[order.id]);
    await client.query("INSERT INTO platform_audit_log(actor_uid,actor_role,action,target_type,target_id,details) VALUES('system','system','dispatch_offer_sent','order',$1,$2::jsonb)",[order.id,JSON.stringify({publicCode:order.public_code,courierId:courier.id})]);
    return "offered";
  });
}

export function startDispatchWorker(pool) {
  if (!pool) return null;
  let running=false;
  const tick=async()=>{
    if(running)return;
    running=true;
    try {
      await expireOffers(pool);
      for(let i=0;i<20;i++){const result=await offerNextCourier(pool);if(result==="none")break;}
    } catch(error) { console.error("Dispatch worker error:",error.message); }
    finally { running=false; }
  };
  void tick();
  return setInterval(tick,5000);
}
