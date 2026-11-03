package uz.alikuryer.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.*
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.layout.ContentScale
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Red=Color(0xFFE20D24)
private val Dark=Color(0xFF151515)
private val Muted=Color(0xFF777B83)
private val Canvas=Color(0xFFF6F6F7)
private data class Food(val id:Int,val title:String,val price:Int,val category:String,val emoji:String,val detail:String)
private data class PlacedOrder(val code:String,val address:String,val total:Int,val items:Int)
private val foods=listOf(
 Food(1,"Cheese Burger",32000,"Burger","🍔","Pishloq, mol go‘shti va sabzavotlar"),
 Food(2,"Double Burger",45000,"Burger","🍔","Ikki kotletli burger"),
 Food(3,"Margarita pitsa",55000,"Pitsa","🍕","Pomidor va mozzarella"),
 Food(4,"Pepperoni pitsa",65000,"Pitsa","🍕","Pepperoni va pishloq"),
 Food(5,"Kartoshka fri",18000,"Setlar","🍟","Qarsildoq kartoshka fri"),
 Food(6,"Coca-Cola 0.5",10000,"Ichimliklar","🥤","Muzdek ichimlik"),
 Food(7,"Lavash",29000,"Burger","🌯","Go‘sht va sabzavotlar"),
 Food(8,"Tovuq set",52000,"Setlar","🍗","Tovuq va fri")
)
private fun sumText(n:Int)=String.format("%,d",n).replace(',',' ')+" so‘m"
class MainActivity:ComponentActivity(){override fun onCreate(savedInstanceState:Bundle?){super.onCreate(savedInstanceState);setContent{MaterialTheme(colorScheme=lightColorScheme(primary=Red,background=Color.White)){AliKuryerApp()}}}}

@Composable private fun AliKuryerApp(){
 var page by remember{mutableStateOf("welcome")}
 var language by remember{mutableStateOf("O‘zbekcha")}
 var phone by remember{mutableStateOf("+998 ")}
 var otp by remember{mutableStateOf("")}
 var category by remember{mutableStateOf("Barchasi")}
 var selectedRestaurant by remember{mutableStateOf("Burger House")}
 var search by remember{mutableStateOf("")}
 var cart by remember{mutableStateOf(mapOf<Int,Int>())}
 var favorites by remember{mutableStateOf(setOf<Int>())}
 var customer by remember{mutableStateOf("")}
 var address by remember{mutableStateOf("")}
 var note by remember{mutableStateOf("")}
 var promo by remember{mutableStateOf("")}
 var promoApplied by remember{mutableStateOf(false)}
 var payment by remember{mutableStateOf("Naqd pul")}
 var order by remember{mutableStateOf<PlacedOrder?>(null)}
 val qty=cart.values.sum()
 val subtotal=foods.sumOf{it.price*(cart[it.id]?:0)}
 val delivery=if(qty>0)12000 else 0
 val discount=if(promoApplied)minOf(10000,subtotal/10) else 0
 val total=subtotal+delivery-discount
 if(page in listOf("welcome","language","phone","otp")){
  Box(Modifier.fillMaxSize().background(if(page=="welcome")Dark else Color.White).padding(26.dp),contentAlignment=Alignment.Center){
   Column(horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.spacedBy(18.dp)){
    Text("🛍",fontSize=58.sp);Text("Ali Kuryer",fontSize=34.sp,fontWeight=FontWeight.Black,color=if(page=="welcome")Color.White else Dark)
    when(page){
     "welcome"->{Text("Taomlaringizni tez va ishonchli yetkazib beramiz!",color=Color.White,textAlign=TextAlign.Center,fontSize=16.sp);Image(painter=painterResource(R.drawable.mascot),contentDescription="Ali Kuryer skuteridagi kuryer bolakay",modifier=Modifier.fillMaxWidth().height(245.dp),contentScale=ContentScale.Fit);Spacer(Modifier.height(8.dp));PrimaryButton("Boshlash  →"){page="language"}}
     "language"->{Text("Tilni tanlang",fontSize=23.sp,fontWeight=FontWeight.Bold,color=Dark);listOf("O‘zbekcha","Русский","中文").forEach{lang->OutlinedButton(onClick={language=lang},modifier=Modifier.fillMaxWidth(),shape=RoundedCornerShape(14.dp)){Text((if(language==lang)"🔴  " else "○  ")+lang,color=Dark,fontSize=17.sp)}};Image(painter=painterResource(R.drawable.mascot),contentDescription="Ali Kuryer bolakay",modifier=Modifier.fillMaxWidth().height(130.dp),contentScale=ContentScale.Fit);PrimaryButton("Davom etish  →"){page="phone"}}
     "phone"->{Image(painter=painterResource(R.drawable.mascot),contentDescription="Skuterda kuryer bolakay",modifier=Modifier.fillMaxWidth().height(155.dp),contentScale=ContentScale.Fit);Text("Telefon raqamingiz",fontSize=23.sp,fontWeight=FontWeight.Bold,color=Dark);OutlinedTextField(phone,{phone=it},modifier=Modifier.fillMaxWidth(),label={Text("Telefon raqami")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Phone),singleLine=true);PrimaryButton("Tasdiqlash kodini yuborish"){page="otp"}}
     "otp"->{Text("Tasdiqlash kodi",fontSize=23.sp,fontWeight=FontWeight.Bold,color=Dark);Text("$phone raqamiga yuborilgan 4 xonali kodni kiriting",color=Muted,textAlign=TextAlign.Center);OutlinedTextField(otp,{if(it.length<=4)otp=it},modifier=Modifier.fillMaxWidth(),label={Text("SMS kodi")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Number),singleLine=true);PrimaryButton("Tasdiqlash"){if(otp.length==4)page="home"}}
    }
   }
  };return
 }
 Scaffold(containerColor=Color.White,bottomBar={if(page in listOf("home","search","cart","orders","profile"))NavigationBar(containerColor=Color.White){listOf("home" to "Asosiy","search" to "Qidiruv","cart" to "Savatcha","orders" to "Buyurtmalar","profile" to "Profil").forEach{(key,label)->NavigationBarItem(selected=page==key,onClick={page=key},icon={Text(when(key){"home"->"⌂";"search"->"⌕";"cart"->"🛒";"orders"->"▤";else->"♙"},fontSize=19.sp)},label={Text(label,fontSize=9.sp)},colors=NavigationBarItemDefaults.colors(selectedIconColor=Red,selectedTextColor=Red,indicatorColor=Color(0xFFFFE8EB)))}}}){pad->
  Column(Modifier.fillMaxSize().padding(pad).background(Color.White)){
   if(page !in listOf("success","tracking","checkout","restaurant"))Row(Modifier.fillMaxWidth().padding(horizontal=16.dp,vertical=12.dp),horizontalArrangement=Arrangement.SpaceBetween,verticalAlignment=Alignment.CenterVertically){Column{Text("🛍 Ali Kuryer",fontSize=23.sp,fontWeight=FontWeight.Black,color=Dark);Text("📍 Namangan  ⌄",fontSize=12.sp,color=Muted)};Text("♡   🛒 $qty",fontSize=19.sp,color=Red,modifier=Modifier.clickable{page="cart"})}
   when(page){
    "home","search"->{val shown=foods.filter{(category=="Barchasi"||it.category==category)&&(it.title+" "+it.detail).contains(search,true)}
     LazyColumn(Modifier.fillMaxSize(),contentPadding=PaddingValues(horizontal=15.dp,vertical=5.dp),verticalArrangement=Arrangement.spacedBy(13.dp)){
      item{Surface(color=Red,shape=RoundedCornerShape(18.dp),modifier=Modifier.fillMaxWidth()){Row(Modifier.padding(18.dp),verticalAlignment=Alignment.CenterVertically){Column(Modifier.weight(1f)){Text("MAZALI TAOMLAR",color=Color.White,fontSize=11.sp);Text("Tez yetkazib beriladi!",color=Color.White,fontSize=23.sp,fontWeight=FontWeight.Black);Text("Sevimli taomingizni tanlang",color=Color.White,fontSize=11.sp)};Image(painter=painterResource(R.drawable.mascot),contentDescription="Skuterda kuryer bolakay",modifier=Modifier.width(105.dp).height(100.dp),contentScale=ContentScale.Fit)}}}
      item{OutlinedTextField(search,{search=it;page="search"},modifier=Modifier.fillMaxWidth(),singleLine=true,placeholder={Text("Restoran, taom yoki mahsulot qidiring")},shape=RoundedCornerShape(25.dp))}
      item{Text("Kategoriyalar",fontSize=19.sp,fontWeight=FontWeight.Bold,color=Dark)}
      item{Row(horizontalArrangement=Arrangement.spacedBy(6.dp)){listOf("Barchasi","Burger","Pitsa","Setlar","Ichimliklar").forEach{c->FilterChip(selected=category==c,onClick={category=c},label={Text(c,fontSize=10.sp)})}}}
      item{Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){Text("Mashhur taomlar",fontSize=19.sp,fontWeight=FontWeight.Bold);Text("Barchasi →",color=Red,fontSize=12.sp,modifier=Modifier.clickable{category="Barchasi"})}}
      items(shown){food->FoodCard(food,cart[food.id]?:0,favorites.contains(food.id),{cart=cart+(food.id to ((cart[food.id]?:0)+1))},{val n=(cart[food.id]?:0)-1;cart=if(n<=0)cart-food.id else cart+(food.id to n)},{favorites=if(food.id in favorites)favorites-food.id else favorites+food.id})}
      if(shown.isEmpty())item{Text("Mahsulot topilmadi",color=Muted)}
     }
    }
    "cart"->Column(Modifier.fillMaxSize().padding(17.dp)){Text("Savatcha",fontSize=25.sp,fontWeight=FontWeight.Black)
     if(qty==0){Spacer(Modifier.height(50.dp));Text("🛒",fontSize=60.sp);Text("Savatchangiz hozircha bo‘sh",fontWeight=FontWeight.Bold)}else{
      LazyColumn(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(8.dp)){items(foods.filter{(cart[it.id]?:0)>0}){f->FoodCard(f,cart[f.id]?:0,false,{cart=cart+(f.id to ((cart[f.id]?:0)+1))},{val n=(cart[f.id]?:0)-1;cart=if(n<=0)cart-f.id else cart+(f.id to n)},{})}}
      OutlinedTextField(promo,{promo=it;promoApplied=false},modifier=Modifier.fillMaxWidth(),singleLine=true,label={Text("Promokod")},trailingIcon={TextButton(onClick={promoApplied=promo.equals("ALI10",true)}){Text("Qo‘llash",color=Red)}})
      if(promoApplied)Text("Chegirma qo‘llandi",color=Color(0xFF16845A))
      PriceLine("Mahsulotlar",subtotal);PriceLine("Yetkazib berish",delivery);if(discount>0)PriceLine("Chegirma",-discount);PriceLine("Jami",total,true)
      PrimaryButton("Buyurtmani rasmiylashtirish  →"){page="checkout"}
     }
    }
    "checkout"->Column(Modifier.fillMaxSize().padding(18.dp),verticalArrangement=Arrangement.spacedBy(11.dp)){Text("Yetkazib berish manzili",fontSize=23.sp,fontWeight=FontWeight.Black)
     Row(horizontalArrangement=Arrangement.spacedBy(8.dp)){listOf("Uy","Ish","Boshqa").forEach{TextButton(onClick={note=it}){Text((if(note==it)"● " else "")+it,color=if(note==it)Red else Dark)}}}
     OutlinedTextField(address,{address=it},modifier=Modifier.fillMaxWidth(),label={Text("Manzil va mo‘ljal")},minLines=2)
     OutlinedTextField(customer,{customer=it},modifier=Modifier.fillMaxWidth(),label={Text("Ismingiz")},singleLine=true)
     OutlinedTextField(phone,{phone=it},modifier=Modifier.fillMaxWidth(),label={Text("Telefon raqami")},keyboardOptions=KeyboardOptions(keyboardType=KeyboardType.Phone),singleLine=true)
     Text("To‘lov usuli",fontWeight=FontWeight.Bold);listOf("Naqd pul","Bank kartasi","Onlayn to‘lov").forEach{method->Surface(shape=RoundedCornerShape(12.dp),border=androidx.compose.foundation.BorderStroke(1.dp,if(payment==method)Red else Color.LightGray),modifier=Modifier.fillMaxWidth().clickable{payment=method}){Text((if(payment==method)"🔴  " else "○  ")+method,Modifier.padding(14.dp),fontWeight=FontWeight.SemiBold)}}
     Spacer(Modifier.weight(1f));PriceLine("Jami",total,true);PrimaryButton("Buyurtma berish  •  "+sumText(total)){if(address.length>=5&&customer.length>=2&&phone.count{it.isDigit()}>=9&&qty>0){order=PlacedOrder("A"+(System.currentTimeMillis()%1000000),address,total,qty);cart=emptyMap();page="success"}}
    }
    "success"->Column(Modifier.fillMaxSize().padding(24.dp),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center){Image(painter=painterResource(R.drawable.mascot),contentDescription="Ali Kuryer bolakay",modifier=Modifier.size(170.dp),contentScale=ContentScale.Fit);Text("✓",fontSize=55.sp,color=Color.White,modifier=Modifier.background(Red,CircleShape).padding(12.dp));Text("Buyurtmangiz qabul qilindi!",fontSize=25.sp,fontWeight=FontWeight.Black,textAlign=TextAlign.Center);Text("Buyurtma raqami",color=Muted);Text(order?.code?:"",fontSize=22.sp,fontWeight=FontWeight.Black,color=Red);Text("Taxminiy yetkazib berish vaqti",color=Muted);Text("20–30 daqiqa",fontSize=21.sp,fontWeight=FontWeight.Bold);PrimaryButton("Buyurtmani kuzatish  →"){page="tracking"};TextButton(onClick={page="home"}){Text("Bosh sahifaga qaytish",color=Dark)}}
    "tracking"->Column(Modifier.fillMaxSize().padding(20.dp),verticalArrangement=Arrangement.spacedBy(18.dp)){Text("←  Buyurtma yo‘lda",fontSize=23.sp,fontWeight=FontWeight.Black,modifier=Modifier.clickable{page="orders"});Surface(color=Canvas,shape=RoundedCornerShape(18.dp),modifier=Modifier.fillMaxWidth().height(250.dp)){Box(contentAlignment=Alignment.Center){Text("📍   ─── 🏍️ ───   🏠",fontSize=30.sp);Text("Xarita kuzatuvi keyingi bosqichda ulanadi",Modifier.align(Alignment.BottomCenter).padding(14.dp),fontSize=11.sp,color=Muted)}};Text("Buyurtma holati",fontSize=19.sp,fontWeight=FontWeight.Bold);Text("● Qabul qilindi   ● Tayyorlanmoqda   ○ Yo‘lda   ○ Yetkazildi",color=Red);Text("Taxminiy vaqt: 20–30 daqiqa",fontSize=20.sp,fontWeight=FontWeight.Bold)}
    "orders"->Column(Modifier.fillMaxSize().padding(18.dp)){Text("Buyurtmalarim",fontSize=25.sp,fontWeight=FontWeight.Black);val o=order;if(o==null)Text("Hozircha buyurtma yo‘q",color=Muted)else Surface(color=Canvas,shape=RoundedCornerShape(15.dp),modifier=Modifier.fillMaxWidth().padding(top=15.dp).clickable{page="tracking"}){Column(Modifier.padding(16.dp),verticalArrangement=Arrangement.spacedBy(7.dp)){Text("🍔  Burger House",fontWeight=FontWeight.Bold);Text("#"+o.code,color=Muted);Text("Qabul qilindi  •  Kuzatish →",color=Red);Text(sumText(o.total),fontWeight=FontWeight.Bold)}}}
    "profile"->Column(Modifier.fillMaxSize().padding(18.dp),verticalArrangement=Arrangement.spacedBy(13.dp)){Text("Profil",fontSize=25.sp,fontWeight=FontWeight.Black);Surface(color=Canvas,shape=RoundedCornerShape(17.dp),modifier=Modifier.fillMaxWidth()){Column(Modifier.padding(18.dp)){Text("🧑🏻‍🍳",fontSize=42.sp);Text(if(customer.isBlank())"Ali Kuryer mijozi" else customer,fontSize=19.sp,fontWeight=FontWeight.Bold);Text(phone,color=Muted)}};listOf("⌖  Mening manzillarim","▣  To‘lov usullari","♡  Sevimli taomlar ("+favorites.size+")","▤  Buyurtmalar tarixi","ⓘ  Yordam va murojaatlar","⚙  Sozlamalar").forEach{item->Surface(color=Color.White,shape=RoundedCornerShape(12.dp),border=androidx.compose.foundation.BorderStroke(1.dp,Color(0xFFECEEF2)),modifier=Modifier.fillMaxWidth().clickable{if(item.contains("Buyurtmalar"))page="orders"}){Text(item,Modifier.padding(15.dp),fontWeight=FontWeight.SemiBold)}};TextButton(onClick={page="welcome"}){Text("Chiqish",color=Red)}}
   }
  }
 }
}

@Composable private fun FoodCard(food:Food,qty:Int,fav:Boolean,onAdd:()->Unit,onMinus:()->Unit,onFav:()->Unit){
 Surface(color=Color.White,shape=RoundedCornerShape(16.dp),border=androidx.compose.foundation.BorderStroke(1.dp,Color(0xFFECEEF2)),modifier=Modifier.fillMaxWidth()){
  Row(Modifier.padding(10.dp),verticalAlignment=Alignment.CenterVertically){Box(Modifier.size(72.dp).background(Color(0xFFFFF1E9),RoundedCornerShape(13.dp)),contentAlignment=Alignment.Center){Text(food.emoji,fontSize=38.sp)}
   Column(Modifier.weight(1f).padding(horizontal=10.dp),verticalArrangement=Arrangement.spacedBy(4.dp)){Text(food.title,fontWeight=FontWeight.Bold,fontSize=14.sp,color=Dark);Text(food.detail,fontSize=10.sp,color=Muted);Text(sumText(food.price),fontSize=13.sp,fontWeight=FontWeight.Bold,color=Red)}
   Column(horizontalAlignment=Alignment.CenterHorizontally){TextButton(onClick=onFav,contentPadding=PaddingValues(0.dp)){Text(if(fav)"♥" else "♡",fontSize=21.sp,color=Red)};if(qty==0)Button(onClick=onAdd,contentPadding=PaddingValues(horizontal=13.dp,vertical=0.dp)){Text("+")}else Row(verticalAlignment=Alignment.CenterVertically){TextButton(onClick=onMinus,contentPadding=PaddingValues(1.dp)){Text("−",color=Red)};Text("$qty",fontWeight=FontWeight.Bold);TextButton(onClick=onAdd,contentPadding=PaddingValues(1.dp)){Text("+",color=Red)}}}
  }
 }
}
@Composable private fun PriceLine(label:String,value:Int,bold:Boolean=false){Row(Modifier.fillMaxWidth().padding(vertical=4.dp),horizontalArrangement=Arrangement.SpaceBetween){Text(label,fontWeight=if(bold)FontWeight.Bold else FontWeight.Normal);Text(sumText(value),fontWeight=if(bold)FontWeight.Black else FontWeight.Medium,color=if(bold)Red else Dark)}}
@Composable private fun PrimaryButton(label:String,onClick:()->Unit){Button(onClick=onClick,modifier=Modifier.fillMaxWidth().height(54.dp),shape=RoundedCornerShape(15.dp),colors=ButtonDefaults.buttonColors(containerColor=Red)){Text(label,fontSize=15.sp,fontWeight=FontWeight.Bold,color=Color.White)}}
