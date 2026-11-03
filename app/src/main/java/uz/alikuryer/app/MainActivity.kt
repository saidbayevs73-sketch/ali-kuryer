package uz.alikuryer.app
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.*
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

private val Red=Color(0xFFE50919)
private data class Dish(val name:String,val price:Int,val emoji:String)
private val dishes=listOf(Dish("Cheese Burger",32000,"🍔"),Dish("Double Burger",45000,"🍔"),Dish("Kartoshka fri",18000,"🍟"),Dish("Coca-Cola",10000,"🥤"))
class MainActivity:ComponentActivity(){override fun onCreate(savedInstanceState:Bundle?){super.onCreate(savedInstanceState);setContent{MaterialTheme(colorScheme=lightColorScheme(primary=Red)){AliApp()}}}}
@Composable private fun AliApp(){
 var page by remember{mutableStateOf("welcome")}; var phone by remember{mutableStateOf("+998 ")}; var address by remember{mutableStateOf("")}; var qty by remember{mutableStateOf(mapOf<String,Int>())}
 val count=qty.values.sum(); val subtotal=dishes.sumOf{it.price*(qty[it.name]?:0)}; val total=subtotal+(if(count>0)12000 else 0)
 Column(Modifier.fillMaxSize().background(Color.White).padding(18.dp)){
 when(page){
 "welcome"->Center("🛵","Ali Kuryer","Tezkor va ishonchli yetkazib berish","Boshlash"){page="language"}
 "language"->{Title("Tilni tanlang");listOf("O‘zbekcha","Русский","中文").forEach{Choice(it){}};Spacer(Modifier.weight(1f));Action("Davom etish"){page="phone"}}
 "phone"->{Title("Telefon raqamingiz");OutlinedTextField(phone,{phone=it},label={Text("Telefon")},modifier=Modifier.fillMaxWidth());Spacer(Modifier.weight(1f));Action("SMS kod olish"){page="otp"}}
 "otp"->Center("🔐","Tasdiqlash kodi","Demo rejim — SMS xizmati ulanmagan","Davom etish"){page="home"}
 "home"->{Title("Ali Kuryer");Text("Namangan bo‘ylab taomlar");CardItem("🍔","Burger House"){page="restaurant"};CardItem("🍕","Pizza Namangan"){page="restaurant"};Spacer(Modifier.weight(1f));Nav(page,{page=it},count)}
 "restaurant"->{Title("Burger House");dishes.forEach{d->Row(Modifier.fillMaxWidth().padding(9.dp),verticalAlignment=Alignment.CenterVertically){Text(d.emoji,fontSize=30.sp);Column(Modifier.weight(1f).padding(start=10.dp)){Text(d.name,fontWeight=FontWeight.Bold);Text(d.price.toString()+" so‘m")};TextButton(onClick={qty=qty+(d.name to ((qty[d.name]?:0)+1))}){Text("Qo‘shish +")}}};Spacer(Modifier.weight(1f));Action("Savatchaga o‘tish"){page="cart"}}
 "cart"->{Title("Savatcha");dishes.filter{(qty[it.name]?:0)>0}.forEach{d->Row(verticalAlignment=Alignment.CenterVertically){Text(d.name,Modifier.weight(1f));TextButton(onClick={val n=(qty[d.name]?:0)-1;qty=if(n<=0)qty-d.name else qty+(d.name to n)}){Text("−")};Text((qty[d.name]?:0).toString());TextButton(onClick={qty=qty+(d.name to ((qty[d.name]?:0)+1))}){Text("+")}}};Spacer(Modifier.weight(1f));Text("Jami: "+total+" so‘m");Action("Rasmiylashtirish"){page="address"}}
 "address"->{Title("Yetkazib berish manzili");OutlinedTextField(address,{address=it},label={Text("Manzil")},modifier=Modifier.fillMaxWidth());Text("To‘lov: yetkazilganda naqd pul");Spacer(Modifier.weight(1f));Action("Buyurtma berish"){page="success"}}
 "success"->Center("✅","Buyurtma qabul qilindi","Demo buyurtma — server ulanmagan","Kuzatish"){page="tracking"}
 "tracking"->Center("🛵","Buyurtma yo‘lda","GPS va kuryer tizimi keyin ulanadi","Buyurtmalar"){page="orders"}
 "orders"->{Title("Buyurtmalarim");Text("Hozircha demo ma’lumot");Spacer(Modifier.weight(1f));Nav(page,{page=it},count)}
 else->{Title("Profil");Text("Telefon: "+phone);Spacer(Modifier.weight(1f));Nav(page,{page=it},count)}
 }
 }
}
@Composable private fun Title(s:String){Text(s,fontSize=24.sp,fontWeight=FontWeight.Black,modifier=Modifier.padding(vertical=18.dp))}
@Composable private fun Action(s:String,go:()->Unit){Button(onClick=go,modifier=Modifier.fillMaxWidth().height(52.dp),shape=RoundedCornerShape(12.dp)){Text(s,fontWeight=FontWeight.Bold)}}
@Composable private fun Center(e:String,t:String,s:String,b:String,go:()->Unit){Column(Modifier.fillMaxSize(),horizontalAlignment=Alignment.CenterHorizontally,verticalArrangement=Arrangement.Center){Text(e,fontSize=64.sp);Text(t,fontSize=24.sp,fontWeight=FontWeight.Black);Text(s,color=Color.Gray);Spacer(Modifier.height(25.dp));Action(b,go)}}
@Composable private fun Choice(s:String,go:()->Unit){Text("○  "+s,Modifier.fillMaxWidth().clickable{go()}.padding(14.dp))}
@Composable private fun CardItem(e:String,s:String,go:()->Unit){Row(Modifier.fillMaxWidth().padding(vertical=8.dp).background(Color(0xFFF5F5F6),RoundedCornerShape(12.dp)).clickable{go()}.padding(16.dp),verticalAlignment=Alignment.CenterVertically){Text(e,fontSize=32.sp);Text(s,Modifier.padding(start=12.dp),fontWeight=FontWeight.Bold)}}
@Composable private fun Nav(page:String,go:(String)->Unit,count:Int){Row(Modifier.fillMaxWidth(),horizontalArrangement=Arrangement.SpaceBetween){listOf("home" to "Asosiy","restaurant" to "Taomlar","cart" to "Savat","orders" to "Buyurtmalar","profile" to "Profil").forEach{(p,t)->Text(t,Modifier.clickable{go(p)}.padding(3.dp),color=if(page==p)Red else Color.DarkGray,fontSize=10.sp)}}}
