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

internal val AliRed = Color(0xFFE02032)
internal val AliBlack = Color(0xFF17171B)
internal val AliMuted = Color(0xFF787981)
internal val AliCanvas = Color(0xFFF7F7F9)
internal val AliBorder = Color(0xFFEAEAF0)

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
internal fun AliWordmark(modifier: Modifier = Modifier, subtitle: Boolean = true) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically) {
        AliMark(size = 45)
        Spacer(Modifier.width(10.dp))
        Column {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("ALI", color = AliRed, fontWeight = FontWeight.Black,
                    fontSize = 21.sp, letterSpacing = (-0.8).sp)
                Text(" KURYER", color = AliBlack, fontWeight = FontWeight.Black,
                    fontSize = 21.sp, letterSpacing = (-0.8).sp)
            }
            if (subtitle) Text("TEZ • QULAY • O‘ZIMIZNIKI",
                color = AliMuted, fontSize = 9.sp,
                fontWeight = FontWeight.SemiBold, letterSpacing = 1.1.sp)
        }
    }
}

@Composable
internal fun AliSectionTitle(title: String, caption: String? = null, trailing: String? = null,
                             onTrailing: (() -> Unit)? = null) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, color = AliBlack, fontSize = 21.sp, fontWeight = FontWeight.ExtraBold)
            if (!caption.isNullOrBlank()) Text(caption, color = AliMuted, fontSize = 12.sp)
        }
        if (trailing != null && onTrailing != null) {
            TextButton(onClick = onTrailing) { Text(trailing, color = AliRed,
                fontWeight = FontWeight.Bold, fontSize = 12.sp) }
        }
    }
}

@Composable
internal fun AliPromoHero(onExplore: () -> Unit) {
    Box(Modifier.fillMaxWidth().height(174.dp)
        .clip(RoundedCornerShape(25.dp))
        .background(Brush.linearGradient(listOf(AliBlack, Color(0xFF3A1C24), AliRed)))) {
        AsyncImage(
            model = "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=1100&q=85",
            contentDescription = null,
            modifier = Modifier.fillMaxSize(),
            contentScale = androidx.compose.ui.layout.ContentScale.Crop,
            alpha = 0.25f
        )
        Row(Modifier.fillMaxSize().padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("BIR BOSISHDA", color = Color(0xFFFFB9BF), fontSize = 11.sp,
                    letterSpacing = 1.4.sp, fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(7.dp))
                Text("Mazali taomlar\neshigingizgacha", color = Color.White,
                    fontSize = 21.sp, fontWeight = FontWeight.Black, lineHeight = 25.sp)
                Spacer(Modifier.height(12.dp))
                Surface(
                    onClick = onExplore, shape = RoundedCornerShape(12.dp),
                    color = Color.White
                ) {
                    Text("Oshxonalarni ko‘rish  →", color = AliBlack,
                        fontWeight = FontWeight.Bold, fontSize = 12.sp,
                        modifier = Modifier.padding(horizontal = 13.dp, vertical = 10.dp))
                }
            }
            Box(Modifier.size(112.dp)
                .clip(CircleShape)
                .background(Color.White.copy(alpha = 0.10f)),
                contentAlignment = Alignment.Center) {
                Box(Modifier.size(91.dp).clip(CircleShape)
                    .background(Color.White.copy(alpha = 0.14f)),
                    contentAlignment = Alignment.Center) {
                    Text("🍔", fontSize = 61.sp)
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
    Column(Modifier.width(80.dp).clickable(onClick = onClick),
        horizontalAlignment = Alignment.CenterHorizontally) {
        Surface(color = Color.White, border = BorderStroke(1.dp, AliBorder),
            shape = RoundedCornerShape(20.dp)) {
            Box(Modifier.size(70.dp), contentAlignment = Alignment.Center) {
                Text(item.icon, fontSize = 31.sp)
                AsyncImage(
                    model = item.photo,
                    contentDescription = item.name,
                    modifier = Modifier.size(70.dp),
                    contentScale = ContentScale.Crop
                )
            }
        }
        Spacer(Modifier.height(7.dp))
        Text(item.name, fontSize = 12.sp, fontWeight = FontWeight.SemiBold,
            color = AliBlack, maxLines = 1)
    }
}

@Composable
internal fun AliRestaurantTile(restaurant: Restaurant, onClick: () -> Unit) {
    Card(onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(23.dp),
        border = BorderStroke(1.dp, AliBorder),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)) {
        Column {
            Box(Modifier.fillMaxWidth().height(125.dp)
                .background(Brush.horizontalGradient(listOf(Color(0xFF221F25),
                    Color(0xFF5B2931), Color(0xFFA9333B))))) {
                val coverUrl = when (restaurant.id % 3) {
                    0 -> "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?auto=format&fit=crop&w=960&q=70"
                    1 -> "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=960&q=70"
                    else -> "https://images.unsplash.com/photo-1552566626-52f8b828add9?auto=format&fit=crop&w=960&q=70"
                }
                AsyncImage(
                    model = coverUrl,
                    contentDescription = null,
                    modifier = Modifier.fillMaxSize(),
                    contentScale = androidx.compose.ui.layout.ContentScale.Crop,
                    alpha = 0.22f
                )
                Row(Modifier.fillMaxSize().padding(17.dp),
                    verticalAlignment = Alignment.CenterVertically) {
                    Box(Modifier.size(71.dp).clip(RoundedCornerShape(20.dp))
                        .background(Color.White.copy(alpha = 0.95f)),
                        contentAlignment = Alignment.Center) {
                        if (restaurant.logoUrl != null) {
                            AsyncImage(model = restaurant.logoUrl,
                                contentDescription = "Oshxona logotipi",
                                modifier = Modifier.size(65.dp))
                        } else {
                            Text("🍽️", fontSize = 35.sp)
                        }
                    }
                    Spacer(Modifier.width(14.dp))
                    Column {
                        Text(restaurant.name, color = Color.White,
                            fontWeight = FontWeight.ExtraBold, fontSize = 20.sp,
                            maxLines = 2, overflow = TextOverflow.Ellipsis)
                        Spacer(Modifier.height(6.dp))
                        Text("TAOMLAR MENYUSI", color = Color.White.copy(alpha = .8f),
                            fontWeight = FontWeight.SemiBold, fontSize = 10.sp,
                            letterSpacing = 1.sp)
                    }
                }
            }
            Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 15.dp),
                verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Default.LocationOn, null, tint = AliRed,
                    modifier = Modifier.size(17.dp))
                Spacer(Modifier.width(5.dp))
                Text(restaurant.address.ifBlank { "Menyuni ko‘rish" },
                    modifier = Modifier.weight(1f),
                    color = AliMuted, maxLines = 1, fontSize = 12.sp,
                    overflow = TextOverflow.Ellipsis)
                Spacer(Modifier.width(7.dp))
                Text("Menyu", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = AliRed)
                Icon(Icons.Default.ChevronRight, null, tint = AliRed,
                    modifier = Modifier.size(20.dp))
            }
        }
    }
}

@Composable
internal fun AliFoodTile(food: Food, count: Int, onPlus: () -> Unit,
                         onMinus: () -> Unit) {
    Surface(modifier = Modifier.fillMaxWidth(),
        color = Color.White, shape = RoundedCornerShape(20.dp),
        border = BorderStroke(1.dp, AliBorder)) {
        Row(Modifier.fillMaxWidth().padding(12.dp),
            verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(102.dp).clip(RoundedCornerShape(16.dp))
                .background(Color(0xFFFFF0EE)),
                contentAlignment = Alignment.Center) {
                if (food.imageUrl != null) {
                    AsyncImage(model = food.imageUrl,
                        contentDescription = food.name,
                        modifier = Modifier.fillMaxSize(),
                        contentScale = androidx.compose.ui.layout.ContentScale.Crop)
                } else {
                    Text("🍲", fontSize = 47.sp)
                }
            }
            Spacer(Modifier.width(13.dp))
            Column(Modifier.weight(1f)) {
                Text(food.name, fontWeight = FontWeight.Bold, color = AliBlack,
                    fontSize = 15.sp, maxLines = 2, overflow = TextOverflow.Ellipsis)
                if (food.category.isNotBlank()) {
                    Text(food.category, color = AliMuted, fontSize = 11.sp,
                        maxLines = 1, overflow = TextOverflow.Ellipsis)
                }
                Spacer(Modifier.height(12.dp))
                Text(priceText(food.price), fontWeight = FontWeight.ExtraBold,
                    color = AliBlack, fontSize = 15.sp)
            }
            Spacer(Modifier.width(5.dp))
            if (count > 0) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    FilledIconButton(onClick = onPlus, modifier = Modifier.size(34.dp),
                        colors = IconButtonDefaults.filledIconButtonColors(
                            containerColor = AliRed, contentColor = Color.White)) {
                        Icon(Icons.Default.Add, "Qo‘shish", modifier = Modifier.size(18.dp))
                    }
                    Text(count.toString(), fontWeight = FontWeight.Bold,
                        modifier = Modifier.padding(5.dp))
                    IconButton(onClick = onMinus, modifier = Modifier.size(30.dp)) {
                        Icon(Icons.Default.Remove, "Kamaytirish",
                            tint = AliBlack, modifier = Modifier.size(18.dp))
                    }
                }
            } else {
                FilledIconButton(onClick = onPlus, modifier = Modifier.size(40.dp),
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = AliRed, contentColor = Color.White)) {
                    Icon(Icons.Default.Add, "Savatga qo‘shish")
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
