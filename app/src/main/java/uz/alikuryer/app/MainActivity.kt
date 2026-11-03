package uz.alikuryer.app
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Red=Color(0xFFDF1728)
private val Ink=Color(0xFF17191F)
private val Soft=Color(0xFFF6F7F9)
private data class Product(val id:Int,val name:String,val price:Int,val category:String,val emoji:String,val info:String)
private data class Order(val code:String,val address:String,val total:Int)
private val catalog=listOf(
 Product(1,"Cheese Burger",32000,"Burger","🍔","Pishloq va yangi sabzavotlar"),
 Product(2,"Double Burger",45000,"Burger","🍔","Ikki kotletli burger"),
 Product(3,"Margarita pitsa",55000,"Pitsa","🍕","Pomidor va mozzarella"),
 Product(4,"Pepperoni pitsa",65000,"Pitsa","🍕","Pepperoni va pishloq"),
 Product(5,"Kartoshka fri",18000,"Burger","🍟","Qarsildoq kartoshka"),
 Product(6,"Coca-Cola 0.5",10000,"Ichimlik","🥤","Sovuq ichimlik"),
 Product(7,"Mevali sharbat",12000,"Ichimlik","🧃","Mevali sharbat"),
 Product(8,"Lavash",29000,"Burger","🌯","Go‘sht va sabzavot")
)
private fun money(n:Int)=String.format("%,d",n).replace(',',' ')+" so‘m"
class MainActivity:ComponentActivity(){override fun onCreate(savedInstanceState:Bundle?){super.onCreate(savedInstanceState);setContent{MaterialTheme(colorScheme=lightColorScheme(primary=Red)){AliApp()}}}}
@Composable private fun AliApp(){
 var page by remember{mutableStateOf("home")}
 var category by remember{mutableStateOf("Barchasi")}
 var query by remember{mutableStateOf("")}
 var cart by remember{mutableStateOf(mapOf<Int,Int>())}
 var favorites by remember{mutableStateOf(setOf<Int>())}
 var name by remember{mutableStateOf("")}
 var phone by remember{mutableStateOf("+998 ")}
 var address by remember{mutableStateOf("")}
 var promo by remember{mutableStateOf("")}
 var promoOk by remember{mutableStateOf(false)}
 var order by remember{mutableStateOf<Order?>(null)}
 val count=cart.values.sum()
 val subtotal=catalog.sumOf{it.price*(cart[it.id]?:0)}
 val delivery=if(count>0)12000 else 0
 val discount=if(promoOk)minOf(10000,subtotal/10) else 0
 val total=subtotal+delivery-discount
 Scaffold(bottomBar={NavigationBar(containerColor=Color.White){listOf("home" to "Asosiy","search" to "Qidiruv","cart" to "Savat","orders" to "Buyurtma","profile" to "Profil").forEach{pair->NavigationBarItem(selected=page==pair.first,onClick={page=pair.first},icon={Text(when(pair.first){"home"->"⌂";"search"->"⌕";"cart"->"🛒";"orders"->"▤";else->"♙"})},label={Text(pair.second,fontSize=10.sp)},colors=NavigationBarItemDefaults.colors(selectedIconColor=Red,selectedTextColor=Red,indicatorColor=Color(0xFFFFE8EA)))}}}){pad->
 Column(Modifier.fillMaxSize().padding(pad).background(Color.White)){
 Row(Modifier.fillMaxWidth().padding(16.dp),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){Column{Text("🛍️ Ali Kuryer",fontSize=22.sp,fontWeight=FontWeight.Black);Text("📍 Namangan · Yetkazib berish",fontSize=11.sp,color=Color.Gray)};Text("🔔",fontSize=22.sp)}
 when(page){
 "home","search"->{
  val shown=catalog.filter{(category=="Barchasi"||it.category==category)&&(it.name+" "+it.info).contains(query,true)}
  LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(horizontal=16.dp,vertical=8.dp),verticalArrangement=Arrangement.spacedBy(11.dp)){
   item{Surface(color=Red,shape=RoundedCornerShape(18.dp),modifier=Modifier.fillMaxWidth()){Column(Modifier.padding(20.dp)){Text("ALI KURYER • NAMANGAN",color=Color(0xFFFFDADD),fontSize=10.sp);Text("Yoqtirganingiz tez yetkaziladi!",color=Color.White,fontSize=24.sp,fontWeight=FontWeight.Black);Text("Taom va mahsulotlar bir joyda.",color=Color.White,fontSize=12.sp)}}}
   item{OutlinedTextField(query,{query=it;page="search"},modifier=Modifier.fillMaxWidth(),singleLine=true,placeholder={Text("Restoran yoki mahsulot qidiring")},shape=RoundedCornerShape(14.dp))}
   item{Text("Kategoriyalar",fontSize=19.sp,fontWeight=FontWeight.Bold)}
   item{Row(horizontalArrangement=Arrangement.spacedBy(5.dp)){listOf("Barchasi","Burger","Pitsa","Ichimlik").forEach{c->FilterChip(selected=category==c,onClick={category=c},label={Text(c,fontSize=10.sp)})}}}
   item{Text("Mashhur taomlar",fontSize=19.sp,fontWeight=FontWeight.Bold)}
   items(shown){p->ProductRow(p,cart[p.id]?:0,favorites.contains(p.id),{cart=cart+(p.id to ((cart[p.id]?:0)+1))},{val n=(cart[p.id]?:0)-1;cart=if(n<=0)cart-p.id else cart+(p.id to n)},{favorites=if(favorites.contains(p.id))favorites-p.id else favorites+p.id})}
   if(shown.isEmpty())item{Text("Hech narsa topilmadi.",color=Color.Gray)}
  }
 }
 "cart"->Column(Modifier.fillMaxSize().padding(18.dp)){Text("Savatcha",fontSize=25.sp,fontWeight=FontWeight.Black)
  if(count==0){Text("🛍️",fontSize=48.sp);Text("Savatingiz bo‘sh",fontWeight=FontWeight.Bold)}else{
   LazyColumn(Modifier.weight(1f)){items(catalog.filter{(cart[it.id]?:0)>0}){p->ProductRow(p,cart[p.id]?:0,false,{cart=cart+(p.id to ((cart[p.id]?:0)+1))},{val n=(cart[p.id]?:0)-1;cart=if(n<=0)cart-p.id else cart+(p.id to n)},{})}}
   OutlinedTextField(promo,{promo=it;promoOk=false},modifier=Modifier.fillMaxWidth(),label={Text("Promo-kod")},trailingIcon={TextButton(onClick={promoOk=promo.trim().equals("ALI10",true)}){Text("Qo‘llash",color=Red)}})
   if(promoOk)Text("10% gacha chegirma qo‘llandi",color=Color(0xFF16845A),fontSize=12.sp)
   Price("Mahsulotlar",subtotal);Price("Yetkazish",delivery);if(discount>0)Price("Chegirma",-discount);Price("Jami",total,true)
   Button(onClick={page="checkout"},modifier=Modifier.fillMaxWidth().height(52.dp)){Text("Rasmiylashtirish")}
  }
 }
 "checkout"->Column(Modifier.fillMaxSize().padding(18.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){Text("Yetkazib berish",fontSize=24.sp,fontWeight=FontWeight.Black)
  OutlinedTextField(name,{name=it},modifier=Modifier.fillMaxWidth(),label={Text("Ismingiz")},singleLine=true)
  OutlinedTextField(phone,{phone=it},modifier=Modifier.fillMaxWidth(),label={Text("Telefon raqamingiz")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Phone),singleLine=true)
  OutlinedTextField(address,{address=it},modifier=Modifier.fillMaxWidth(),label={Text("Manzil va mo‘ljal")},minLines=2)
  Text("To‘lov: yetkazilganda naqd pul",color=Red,fontWeight=FontWeight.Bold)
  Text("Xarita orqali manzil tanlash keyingi integratsiya bosqichida ulanadi.",fontSize=11.sp,color=Color.Gray)
  Spacer(Modifier.weight(1f));Price("Jami",total,true)
  Button(onClick={if(name.trim().length>=2&&phone.count{it.isDigit()}>=9&&address.trim().length>=5&&count>0){order=Order("AK-"+(System.currentTimeMillis()%1000000),address,total);cart=emptyMap();page="success"}},modifier=Modifier.fillMaxWidth().height(52.dp)){Text("Buyurtma berish")}
 }
 "success"->Column(Modifier.fillMaxSize().padding(24.dp),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center){Text("✅",fontSize=60.sp);Text("Buyurtmangiz qabul qilindi!",fontSize=23.sp,fontWeight=FontWeight.Black);Text(order?.code?: "",color=Red,fontWeight=FontWeight.Bold);Text("To‘lov: naqd pul",color=Color.Gray);Button(onClick={page="orders"}){Text("Buyurtmani kuzatish")}}
 "orders"->Column(Modifier.fillMaxSize().padding(18.dp)){Text("Buyurtmalarim",fontSize=25.sp,fontWeight=FontWeight.Black);val o=order;if(o==null)Text("Hozircha buyurtma yo‘q.",color=Color.Gray)else Surface(color=Soft,shape=RoundedCornerShape(15.dp),modifier=Modifier.fillMaxWidth().padding(top=15.dp)){Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(8.dp)){Text(o.code,color=Red,fontWeight=FontWeight.Bold);Text("Buyurtma qabul qilindi",fontWeight=FontWeight.Bold);Text("Tayyorlanmoqda  →  Kuryer yo‘lda  →  Yetkazildi",fontSize=12.sp);Text("Manzil: "+o.address,fontSize=12.sp);Text("Jami: "+money(o.total),fontWeight=FontWeight.Bold)}}}
 "profile"->Column(Modifier.fillMaxSize().padding(18.dp),verticalArrangement=Arrangement.spacedBy(12.dp)){Text("Profil",fontSize=25.sp,fontWeight=FontWeight.Black);Surface(color=Soft,shape=RoundedCornerShape(16.dp),modifier=Modifier.fillMaxWidth()){Column(Modifier.padding(18.dp)){Text("👤",fontSize=36.sp);Text(if(name.isBlank())"Ali Kuryer mijozi" else name,fontWeight=FontWeight.Bold,fontSize=18.sp);Text(phone,color=Color.Gray)}};listOf("♡  Sevimlilar ("+favorites.size+")","⌖  Saqlangan manzillar","▤  Buyurtmalar tarixi","ⓘ  Yordam va murojaatlar","⚙  Sozlamalar").forEach{Surface(color=Color.White,shape=RoundedCornerShape(12.dp),border=androidx.compose.foundation.BorderStroke(1.dp,Color(0xFFECEEF2)),modifier=Modifier.fillMaxWidth().clickable{if(it.startsWith("♡")){category="Barchasi";page="home"}}){Text(it,Modifier.padding(15.dp),fontWeight=FontWeight.SemiBold)}}}
 }
 }
}}
@Composable private fun ProductRow(p:Product,qty:Int,fav:Boolean,onAdd:()->Unit,onMinus:()->Unit,onFav:()->Unit){
 Surface(color=Color.White,shape=RoundedCornerShape(15.dp),border=androidx.compose.foundation.BorderStroke(1.dp,Color(0xFFECEEF2)),modifier=Modifier.fillMaxWidth()){
 Row(Modifier.padding(10.dp),verticalAlignment=Alignment.CenterVertically){Box(Modifier.size(62.dp).background(Color(0xFFFFF1E9),RoundedCornerShape(12.dp)),contentAlignment=Alignment.Center){Text(p.emoji,fontSize=32.sp)}
 Column(Modifier.weight(1f).padding(horizontal=10.dp),verticalArrangement=Arrangement.spacedBy(3.dp)){Text(p.name,fontWeight=FontWeight.Bold,fontSize=13.sp);Text(p.info,fontSize=10.sp,color=Color.Gray);Text(money(p.price),fontSize=12.sp,fontWeight=FontWeight.Bold,color=Red)}
 Column(horizontalAlignment=Alignment.CenterHorizontally){TextButton(onClick=onFav,contentPadding=PaddingValues(0.dp)){Text(if(fav)"♥" else "♡",color=Red,fontSize=18.sp)};if(qty==0)Button(onClick=onAdd,contentPadding=PaddingValues(horizontal=12.dp,vertical=3.dp)){Text("+")}else{Row(verticalAlignment=Alignment.CenterVertically){TextButton(onClick=onMinus,contentPadding=PaddingValues(1.dp)){Text("−")};Text(qty.toString(),fontWeight=FontWeight.Bold);TextButton(onClick=onAdd,contentPadding=PaddingValues(1.dp)){Text("+")}}}}
 }
 }
}
@Composable private fun Price(label:String,value:Int,bold:Boolean=false){Row(Modifier.fillMaxWidth().padding(vertical=4.dp),horizontalArrangement=Arrangement.SpaceBetween){Text(label,fontWeight=if(bold)FontWeight.Bold else FontWeight.Normal);Text(money(value),fontWeight=if(bold)FontWeight.Black else FontWeight.Medium,color=if(bold)Red else Ink)}}
