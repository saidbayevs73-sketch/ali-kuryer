package uz.alikuryer.customer

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.BrightnessAuto
import androidx.compose.material.icons.filled.DarkMode
import androidx.compose.material.icons.filled.LightMode
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.text.font.FontWeight

/** Local appearance choices work for signed-in and guest customers. */
@Composable
internal fun AliAppearanceSelector(mode: String, onChange: (String) -> Unit) {
    Surface(shape = RoundedCornerShape(18.dp), color = AliSurface,
        border = BorderStroke(1.dp, AliBorder)) {
        Column(Modifier.fillMaxWidth().padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Text("Ko‘rinish", fontWeight = FontWeight.ExtraBold,
                fontSize = 17.sp, color = AliBlack)
            Text("Ilova fonini tanlang. Tanlov telefonda saqlanadi.",
                fontSize = 12.sp, color = AliMuted)
            listOf(
                Triple("light", "Oq fon", "Yorug‘ rejim"),
                Triple("dark", "Qora fon", "Tungi rejim"),
                Triple("system", "Avtomatik", "Telefon sozlamasiga mos")
            ).forEach { (value, title, subtitle) ->
                Row(
                    Modifier.fillMaxWidth().clickable { onChange(value) }.padding(vertical = 8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        when (value) {
                            "light" -> Icons.Default.LightMode
                            "dark" -> Icons.Default.DarkMode
                            else -> Icons.Default.BrightnessAuto
                        },
                        contentDescription = null,
                        tint = if (mode == value) AliRed else AliMuted
                    )
                    Spacer(Modifier.width(13.dp))
                    Column(Modifier.weight(1f)) {
                        Text(title, fontWeight = FontWeight.Bold, color = AliBlack)
                        Text(subtitle, fontSize = 11.sp, color = AliMuted)
                    }
                    RadioButton(selected = mode == value, onClick = null,
                        colors = RadioButtonDefaults.colors(selectedColor = AliRed))
                }
            }
        }
    }
}
