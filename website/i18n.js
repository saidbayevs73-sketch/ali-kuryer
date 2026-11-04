(function(){
"use strict";
const translations={
ru:{
"Joylashuv:":"Местоположение:","O‘zbekiston (avtomatik)":"Узбекистан (автоматически)","Kirish":"Войти","Restoranlar":"Рестораны","Do‘konlar":"Магазины","Aksiyalar":"Акции","Kategoriyalar":"Категории","Bugungi takliflar":"Предложения дня","Mashhur restoranlar":"Популярные рестораны","Ommabop mahsulotlar":"Популярные товары","Tez yetkazish":"Быстрая доставка","Savatcha va buyurtma":"Корзина и заказ","Yetkazib berish ma’lumotlari":"Данные доставки","Ismingiz":"Ваше имя","Telefon raqamingiz":"Ваш номер телефона","Manzil":"Адрес","Jami":"Итого","Buyurtmani tasdiqlash":"Подтвердить заказ","Bosh sahifa":"Главная","Katalog":"Каталог","Savat":"Корзина","Kabinet":"Кабинет","Yetkazib berish manzili":"Адрес доставки","Hozirgi joylashuvimni aniqlash":"Определить моё местоположение","Manzilni saqlash":"Сохранить адрес","Saqlangan manzillar":"Сохранённые адреса","Tanlash":"Выбрать","Buyurtmalarim":"Мои заказы","Yetkazib berish manzillari":"Адреса доставки","Saralanganlar":"Избранное","Savol-javob":"Вопросы и ответы","Biz bilan bog‘lanish":"Связаться с нами","Ilovani o‘rnatish":"Установить приложение","Yopish":"Закрыть"
},
zh:{
"Joylashuv:":"位置：","O‘zbekiston (avtomatik)":"乌兹别克斯坦（自动）","Kirish":"登录","Restoranlar":"餐厅","Do‘konlar":"商店","Aksiyalar":"优惠活动","Kategoriyalar":"分类","Bugungi takliflar":"今日推荐","Mashhur restoranlar":"热门餐厅","Ommabop mahsulotlar":"热门商品","Tez yetkazish":"快速配送","Savatcha va buyurtma":"购物车和订单","Yetkazib berish ma’lumotlari":"配送信息","Ismingiz":"姓名","Telefon raqamingiz":"电话号码","Manzil":"地址","Jami":"合计","Buyurtmani tasdiqlash":"确认订单","Bosh sahifa":"首页","Katalog":"商品目录","Savat":"购物车","Kabinet":"个人中心","Yetkazib berish manzili":"配送地址","Hozirgi joylashuvimni aniqlash":"定位我的位置","Manzilni saqlash":"保存地址","Saqlangan manzillar":"已保存地址","Tanlash":"选择","Buyurtmalarim":"我的订单","Yetkazib berish manzillari":"配送地址","Saralanganlar":"收藏","Savol-javob":"常见问题","Biz bilan bog‘lanish":"联系我们","Ilovani o‘rnatish":"安装应用","Yopish":"关闭"
}};
const current=()=>localStorage.getItem("aliLanguage")||"uz";
function apply(root){
 const map=translations[current()];if(!map)return;
 const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT),nodes=[];
 while(walker.nextNode())nodes.push(walker.currentNode);
 nodes.forEach(node=>{const key=node.nodeValue.trim();if(map[key])node.nodeValue=node.nodeValue.replace(key,map[key]);});
 root.querySelectorAll?.("[placeholder]").forEach(el=>{const value=el.getAttribute("placeholder");if(map[value])el.setAttribute("placeholder",map[value]);});
}
function setLanguage(lang){if(!["uz","ru","zh"].includes(lang))return;localStorage.setItem("aliLanguage",lang);document.documentElement.lang=lang==="zh"?"zh-CN":lang;location.reload();}
window.AliKuryerI18n={setLanguage,getLanguage:current};
if(current()!=="uz"){
 const start=()=>{apply(document);new MutationObserver(records=>records.forEach(record=>record.addedNodes.forEach(node=>{if(node.nodeType===1)apply(node);else if(node.nodeType===3){const map=translations[current()];const key=node.nodeValue.trim();if(map?.[key])node.nodeValue=node.nodeValue.replace(key,map[key]);}}))).observe(document.body,{childList:true,subtree:true});};
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",start);else start();
}
})();