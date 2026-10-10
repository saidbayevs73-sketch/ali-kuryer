package uz.alikuryer.customer

import androidx.compose.foundation.background
import androidx.compose.foundation.Image
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.compositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import java.util.Locale

internal val AliRed = Color(0xFFE50914)
/** All customer screens inherit the selected color mode. */
internal val LocalAliDark = compositionLocalOf { false }
internal val AliBlack: Color
    @Composable get() = if (LocalAliDark.current) Color(0xFFF4F4F6) else Color(0xFF111111)
internal val AliMuted: Color
    @Composable get() = if (LocalAliDark.current) Color(0xFFAFB2BB) else Color(0xFF787981)
internal val AliCanvas: Color
    @Composable get() = if (LocalAliDark.current) Color(0xFF101114) else Color(0xFFF0F0F0)
internal val AliSurface: Color
    @Composable get() = if (LocalAliDark.current) Color(0xFF1B1D21) else Color(0xFFFAFAFA)
internal val AliBorder: Color
    @Composable get() = if (LocalAliDark.current) Color(0xFF343740) else Color(0xFFE8E8E8)

internal fun priceText(value: Long): String =
    "%,d".format(Locale.US, value).replace(",", " ") + " so‘m"

@Composable
internal fun AliMark(modifier: Modifier = Modifier, size: Int = 43) {
    Image(
        painter = painterResource(id = R.drawable.ali_kuryer_user_logo),
        contentDescription = "Ali Kuryer original logotipi",
        modifier = modifier.size(size.dp).clip(RoundedCornerShape((size / 4).dp)),
        contentScale = ContentScale.Fit
    )
}

@Composable
internal fun AliWordmark(modifier: Modifier = Modifier, subtitle: Boolean = true, darkHeader: Boolean = false) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        AliMark(size = 45)
        Spacer(Modifier.width(10.dp))
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("ALI", color = AliRed, fontWeight = FontWeight.Black,
                    fontSize = 21.sp, letterSpacing = (-0.8).sp)
                Text(" KURYER", color = if (darkHeader) Color.White else AliBlack, fontWeight = FontWeight.Black,
                    fontSize = 21.sp, letterSpacing = (-0.8).sp)
            }
            if (subtitle) Text("TEZ • QULAY • O‘ZIMIZNIKI",
                color = if (darkHeader) Color.LightGray else AliMuted, fontSize = 9.sp,
                fontWeight = FontWeight.SemiBold, letterSpacing = 1.1.sp)
        }
    }
}

@Composable
internal fun AliSectionTitle(title: String, caption: String? = null, trailing: String? = null,
                             onTrailing: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, color = AliBlack, fontSize = 24.sp, fontWeight = FontWeight.ExtraBold)
            if (!caption.isNullOrBlank()) Text(caption, color = AliMuted, fontSize = 14.sp)
        }
        if (trailing != null && onTrailing != null) {
            TextButton(onClick = onTrailing) { Text(trailing, color = AliRed,
                fontWeight = FontWeight.Bold, fontSize = 12.sp) }
        }
    }
}

@Composable
internal fun AliPromoHero(onExplore: () -> Unit) {
    Box(Modifier.fillMaxWidth().height(290.dp)
        .clip(RoundedCornerShape(22.dp)).background(Color(0xFF101010))) {
        AsyncImage(
            model = "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1400&q=88",
            contentDescription = "Haqiqiy taomlar fotosurati",
            modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop
        )
        Box(Modifier.fillMaxSize().background(
            Brush.horizontalGradient(listOf(Color(0xE9000000), Color(0xAA000000), Color(0x08000000)))
        ))
        Column(Modifier.fillMaxHeight().widthIn(max = 290.dp)
            .padding(start = 21.dp, top = 27.dp, end = 5.dp, bottom = 22.dp),
            verticalArrangement = Arrangement.SpaceBetween) {
            Column {
                Text("ALI KURYER", color = Color(0xFFFF606A),
                    fontWeight = FontWeight.ExtraBold, fontSize = 12.sp)
                Spacer(Modifier.height(13.dp))
                Text("Sevimli taomingiz\neshigingizgacha.",
                    color = Color.White, fontSize = 30.sp,
                    lineHeight = 34.sp, fontWeight = FontWeight.Black)
                Spacer(Modifier.height(10.dp))
                Text("Haqiqiy oshxonalar. Mazali taomlar. Tez yetkazish.",
                    fontSize = 13.sp, lineHeight = 18.sp, color = Color(0xFFF0F0F0))
            }
            Button(onClick = onExplore, shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = AliRed),
                modifier = Modifier.heightIn(min = 48.dp)) {
                Icon(Icons.Default.RestaurantMenu, null, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(7.dp))
                Text("Oshxonalarni ko‘rish", fontSize = 13.sp,
                    fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
internal fun AliServiceHighlights() {
    Surface(color = Color(0xFF080808), shape = RoundedCornerShape(18.dp)) {
        Row(Modifier.fillMaxWidth().padding(vertical = 16.dp, horizontal = 7.dp),
            horizontalArrangement = Arrangement.SpaceEvenly) {
            val highlights = listOf(
                Triple("Tez yetkazish", "Buyurtmani kuzating", Icons.Default.LocalShipping),
                Triple("GPS manzil", "Aniq yetkazish", Icons.Default.LocationOn),
                Triple("Haqiqiy menyu", "Oshxona taomlari", Icons.Default.Restaurant)
            )
            highlights.forEach { (title, detail, image) ->
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(image, null, tint = Color(0xFFFF3443),
                        modifier = Modifier.size(22.dp))
                    Spacer(Modifier.height(6.dp))
                    Text(title, color = Color.White, fontSize = 10.sp,
                        fontWeight = FontWeight.Bold, maxLines = 1)
                    Text(detail, color = Color(0xFFBDBDBD), fontSize = 9.sp,
                        maxLines = 1)
                }
            }
        }
    }
}

internal data class QuickCategory(
    val icon: String, val name: String, val query: String, val photo: String
)
internal val quickCategories = listOf(
    QuickCategory("🍔", "Burger", "burger",
        "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=250&q=78"),
    QuickCategory("🌯", "Lavash", "lavash",
        "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=250&q=78"),
    QuickCategory("🍕", "Pizza", "pizza",
        "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=250&q=78"),
    QuickCategory("🍚", "Milliy", "osh",
        "https://images.unsplash.com/photo-1604908176997-4311bb7e970a?auto=format&fit=crop&w=250&q=78"),
    QuickCategory("🥗", "Salat", "salat",
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=250&q=78"),
    QuickCategory("🥤", "Ichimlik", "ichimlik",
        "https://images.unsplash.com/photo-1544145945-f90425340c7e?auto=format&fit=crop&w=250&q=78")
)

@Composable
internal fun AliCategoryTile(item: QuickCategory, onClick: () -> Unit) {
    Column(Modifier.width(108.dp).clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally) {
        Surface(color = AliSurface, border = BorderStroke(1.dp, AliBorder),
            shape = RoundedCornerShape(16.dp)) {
            Box(Modifier.size(width = 108.dp, height = 100.dp)
                .background(AliCanvas), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.Restaurant, null, tint = AliMuted)
                AsyncImage(model = item.photo, contentDescription = item.name,
                    modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
            }
        }
        Spacer(Modifier.height(7.dp))
        Text(item.name, fontSize = 14.sp, fontWeight = FontWeight.Bold,
            color = AliBlack, maxLines = 1)
    }
}

@Composable
internal fun AliRestaurantTile(restaurant: Restaurant, onClick: () -> Unit) {
    Card(onClick = onClick, modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(21.dp),
        border = BorderStroke(1.dp, AliBorder),
        colors = CardDefaults.cardColors(containerColor = AliSurface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column {
            val cover = when (restaurant.id % 3) {
                0 -> "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=1100&q=85"
                1 -> "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=1100&q=85"
                else -> "https://images.unsplash.com/photo-1552566626-52f8b828add9?auto=format&fit=crop&w=1100&q=85"
            }
            Box(Modifier.fillMaxWidth().height(205.dp)
                .background(Color(0xFF292929))) {
                AsyncImage(model = cover,
                    contentDescription = "Restoran muhiti, namunaviy fotosurat",
                    modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                Surface(modifier = Modifier.align(Alignment.TopEnd).padding(12.dp),
                    color = Color(0xC0000000),
                    shape = RoundedCornerShape(8.dp)) {
                    Text("Namunaviy surat", color = Color.White, fontSize = 10.sp,
                        modifier = Modifier.padding(horizontal = 9.dp, vertical = 5.dp))
                }
            }
            Row(Modifier.fillMaxWidth().padding(17.dp),
                verticalAlignment = Alignment.CenterVertically) {
                if (!restaurant.logoUrl.isNullOrBlank()) {
                    AsyncImage(model = restaurant.logoUrl,
                        contentDescription = restaurant.name + " logotipi",
                        modifier = Modifier.size(55.dp)
                            .clip(RoundedCornerShape(11.dp)),
                        contentScale = ContentScale.Fit)
                    Spacer(Modifier.width(10.dp))
                }
                Column(Modifier.weight(1f)) {
                    Text(restaurant.name, fontSize = 21.sp,
                        fontWeight = FontWeight.ExtraBold, color = AliBlack,
                        maxLines = 2, overflow = TextOverflow.Ellipsis)
                    Spacer(Modifier.height(6.dp))
                    Text(restaurant.address.ifBlank { "Taomlar va menyu" },
                        fontSize = 13.sp, maxLines = 2,
                        color = AliMuted, overflow = TextOverflow.Ellipsis)
                }
                Spacer(Modifier.width(8.dp))
                Surface(shape = RoundedCornerShape(10.dp), color = AliRed) {
                    Icon(Icons.Default.ChevronRight, "Menyuni ochish",
                        tint = Color.White,
                        modifier = Modifier.size(40.dp).padding(7.dp))
                }
            }
        }
    }
}

@Composable
internal fun AliFoodTile(food: Food, count: Int,
                         onPlus: () -> Unit, onMinus: () -> Unit) {
    Surface(modifier = Modifier.fillMaxWidth(), color = AliSurface,
        shape = RoundedCornerShape(21.dp),
        border = BorderStroke(1.dp, AliBorder)) {
        Row(Modifier.fillMaxWidth().padding(10.dp),
            verticalAlignment = Alignment.CenterVertically) {
            val sample = food.imageUrl.isNullOrBlank()
            Box(Modifier.size(width = 142.dp, height = 146.dp)
                .clip(RoundedCornerShape(15.dp))
                .background(AliCanvas), contentAlignment = Alignment.Center) {
                Icon(Icons.Default.Restaurant, null, tint = AliMuted)
                AsyncImage(
                    model = food.imageUrl ?: "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=600&q=85",
                    contentDescription = if (sample) "Namunaviy taom fotosurati" else food.name,
                    modifier = Modifier.fillMaxSize(), contentScale = ContentScale.Crop)
                if (sample) Surface(modifier = Modifier.align(Alignment.BottomStart)
                    .padding(6.dp), shape = RoundedCornerShape(6.dp),
                    color = Color(0xD0000000)) {
                    Text("Namuna", color = Color.White, fontSize = 9.sp,
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp))
                }
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f),
                verticalArrangement = Arrangement.spacedBy(7.dp)) {
                Text(food.name, color = AliBlack, fontSize = 17.sp,
                    lineHeight = 20.sp, fontWeight = FontWeight.ExtraBold,
                    maxLines = 3, overflow = TextOverflow.Ellipsis)
                if (food.category.isNotBlank())
                    Text(food.category, fontSize = 12.sp, color = AliMuted, maxLines = 1)
                Text(priceText(food.price), color = AliBlack,
                    fontSize = 17.sp, lineHeight = 20.sp,
                    fontWeight = FontWeight.Black)
                if (count > 0) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        IconButton(onClick = onMinus, modifier = Modifier.size(35.dp)) {
                            Icon(Icons.Default.Remove, "Kamaytirish", tint = AliBlack)
                        }
                        Text(count.toString(), fontWeight = FontWeight.ExtraBold)
                        FilledIconButton(onClick = onPlus, modifier = Modifier.size(37.dp),
                            colors = IconButtonDefaults.filledIconButtonColors(
                                containerColor = AliRed, contentColor = Color.White)) {
                            Icon(Icons.Default.Add, "Qo‘shish")
                        }
                    }
                } else {
                    Button(onClick = onPlus, shape = RoundedCornerShape(10.dp),
                        contentPadding = PaddingValues(horizontal = 10.dp, vertical = 8.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = AliRed)) {
                        Icon(Icons.Default.Add, null, modifier = Modifier.size(17.dp))
                        Spacer(Modifier.width(4.dp))
                        Text("Qo‘shish", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                    }
                }
            }
        }
    }
}

@Composable
internal fun AliEmptyState(icon: String, title: String, subtitle: String,
                           button: String? = null, onClick: (() -> Unit)? = null) {
    Column(Modifier.fillMaxWidth().padding(vertical = 31.dp, horizontal = 15.dp),
        horizontalAlignment = Alignment.CenterHorizontally) {
        Box(Modifier.size(91.dp).clip(CircleShape)
            .background(Color(0xFFFFE7EA)), contentAlignment = Alignment.Center) {
            Text(icon, fontSize = 44.sp)
        }
        Spacer(Modifier.height(16.dp))
        Text(title, color = AliBlack, fontWeight = FontWeight.ExtraBold, fontSize = 17.sp)
        Spacer(Modifier.height(8.dp))
        Text(subtitle, color = AliMuted, fontSize = 13.sp,
            lineHeight = 18.sp, modifier = Modifier.padding(horizontal = 12.dp))
        if (button != null && onClick != null) {
            Spacer(Modifier.height(17.dp))
            Button(onClick = onClick, shape = RoundedCornerShape(13.dp),
                colors = ButtonDefaults.buttonColors(containerColor = AliRed)) {
                Text(button, fontWeight = FontWeight.Bold)
            }
        }
    }
}
