import streamlit as st
st.markdown('<meta name="google-site-verification" content="BlGcjiTJXeG-AtnkqqMBVQ4J3KdhpZmJSc7QqtJPQlo" />', unsafe_allow_html=True)
import streamlit as st
import feedparser
import time
import re
import requests
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Küresel Gündem | Dünya Haberleri",
    page_icon="🌐",
    layout="centered"
)

# Türkçe Ay İsimleri
TURKCE_AYLAR = {
    1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
    7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
}

def html_ve_karakter_temizle(ham_metin):
    """HTML etiketlerini ve özel karakterleri temizler."""
    if not ham_metin:
        return ""
    temizleyici = re.compile('<.*?>')
    temiz = re.sub(temizleyici, '', ham_metin)
    temiz = temiz.replace('&amp;', '&').replace('&nbsp;', ' ').replace('&quot;', '"')
    temiz = temiz.replace('‘', "'").replace('’', "'").replace('“', '"').replace('”', '"')
    temiz = temiz.split("See more headlines")[0].split("Google News")[0]
    return temiz.strip()

def direkt_google_cevir(metin):
    """Doğrudan Google API kullanarak %100 Türkçe çeviri sağlar."""
    if not metin or metin.strip() == "":
        return ""
    
    temiz_metin = html_ve_karakter_temizle(metin)
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "en", "tl": "tr", "dt": "t", "q": temiz_metin}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        if response.status_code == 200:
            json_data = response.json()
            return "".join([parca[0] for parca in json_data[0] if parca[0]])
    except Exception:
        pass
    return temiz_metin

def turkiye_saatine_cevir(tarih_metni):
    """GMT tarihini Türkiye Saatine (TSİ UTC+3) dönüştürür."""
    try:
        dt_utc = parsedate_to_datetime(tarih_metni)
        dt_tsi = dt_utc + timedelta(hours=3)
        return f"{dt_tsi.day} {TURKCE_AYLAR[dt_tsi.month]} {dt_tsi.year} | {dt_tsi.strftime('%H:%M')} (TSİ)"
    except Exception:
        return tarih_metni

def kategori_etiketi_al(metin):
    """Haberin konusuna göre Türkçe etiket ve renk belirler."""
    kucuk_metin = metin.lower()
    if any(k in kucuk_metin for k in ['savaş', 'kriz', 'saldırı', 'acil', 'war', 'crisis', 'attack', 'emergency', 'trump', 'nobel']):
        return "🔥 SON DAKİKA", "#e74c3c"
    elif any(k in kucuk_metin for k in ['ekonomi', 'piyasa', 'dolar', 'faiz', 'economy', 'market', 'bank']):
        return "📊 EKONOMİ", "#27ae60"
    elif any(k in kucuk_metin for k in ['teknoloji', 'uzay', 'ai', 'tech', 'google', 'apple']):
        return "🚀 TEKNOLOJİ", "#2980b9"
    else:
        return "🌍 DÜNYA GÜNDEMİ", "#8e44ad"

def onem_puani_hesapla(metin):
    """Haberin önem derecesini puanlar."""
    kucuk_metin = metin.lower()
    puan = 0
    if any(k in kucuk_metin for k in ['war', 'crisis', 'emergency', 'election', 'savaş', 'kriz', 'seçim', 'trump', 'nobel', 'saldırı']):
        puan += 3
    if any(k in kucuk_metin for k in ['economy', 'tech', 'ekonomi', 'teknoloji']):
        puan += 1
    return puan

@st.cache_data(ttl=1800) # Haberleri 30 dakikada bir önbelleğe alır (siteyi hızlandırır)
def haberleri_getir_ve_sirala():
    url = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    akis = feedparser.parse(url)
    if not akis.entries:
        return []
    
    bugun = datetime.now().date()
    haber_listesi = []
    
    for haber in akis.entries:
        if hasattr(haber, 'published_parsed') and haber.published_parsed:
            haber_tarihi = datetime(*haber.published_parsed[:3]).date()
            if haber_tarihi == bugun:
                ham_baslik = haber.title
                baglanti = haber.link
                yayin_tarihi_ham = haber.published
                
                temiz_ozet = html_ve_karakter_temizle(getattr(haber, 'summary', ''))
                tsi_tarih = turkiye_saatine_cevir(yayin_tarihi_ham)
                
                if " - " in ham_baslik:
                    baslik_parcalari = ham_baslik.rsplit(" - ", 1)
                    ingilizce_baslik, kaynak = baslik_parcalari[0], baslik_parcalari[1]
                else:
                    ingilizce_baslik, kaynak = ham_baslik, "Küresel Ajans"
                    
                kaynak = html_ve_karakter_temizle(kaynak)
                
                turkce_baslik = direkt_google_cevir(ingilizce_baslik)
                time.sleep(0.05)
                turkce_ozet = direkt_google_cevir(temiz_ozet[:250]) if temiz_ozet else ""
                time.sleep(0.05)
                
                onem = onem_puani_hesapla(ingilizce_baslik + " " + turkce_baslik)
                etiket_metni, etiket_rengi = kategori_etiketi_al(turkce_baslik)
                
                haber_listesi.append({
                    "baslik": turkce_baslik,
                    "ozet": turkce_ozet if turkce_ozet else "Detaylar için haber kaynağını ziyaret edebilirsiniz.",
                    "kaynak": kaynak,
                    "tarih": tsi_tarih,
                    "link": baglanti,
                    "onem": onem,
                    "etiket": etiket_metni,
                    "renk": etiket_rengi
                })
                
        if len(haber_listesi) >= 25:
            break
            
    return sorted(haber_listesi, key=lambda x: x['onem'], reverse=True)[:12]

# --- SİTE ARAYÜZÜ (GÜVEN VEREN TASARIM) ---

st.title("🌐 DÜNYA HABER PORTALI")
st.caption("Güvenilir, tarafsız ve anlık küresel gelişme derlemesi.")
st.markdown("---")

with st.spinner("🌍 Küresel haber akışı taranıyor ve Türkçeye derleniyor..."):
    sirali_haberler = haberleri_getir_ve_sirala()

if not sirali_haberler:
    st.info("ℹ️ Bugüne ait eşleşen güncel haber henüz akışa düşmemiş olabilir.")
else:
    for oge in sirali_haberler:
        # Streamlit kart görünümü
        st.markdown(
            f"""
            <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; margin-bottom: 15px; border-left: 5px solid {oge['renk']}; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="background-color: {oge['renk']}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">{oge['etiket']}</span>
                    <span style="color: #888; font-size: 12px;">🕒 {oge['tarih']}</span>
                </div>
                <h3 style="color: #2c3e50; margin: 5px 0 10px 0; font-size: 18px;">{oge['baslik']}</h3>
                <p style="color: #555; font-size: 14px; line-height: 1.5; margin-bottom: 12px;">{oge['ozet']}</p>
                <div style="display: flex; justify-content: space-between; align-items: center; border-top: 1px solid #eee; padding-top: 10px;">
                    <span style="color: #666; font-size: 13px; font-weight: 600;">🏛️ Kaynak: {oge['kaynak']}</span>
                    <a href="{oge['link']}" target="_blank" style="background-color: #2980b9; color: white; padding: 6px 12px; border-radius: 5px; text-decoration: none; font-size: 12px; font-weight: bold;">Habere Git ➔</a>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

# Altbilgi (Güven ve Şeffaflık)
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: #7f8c8d; font-size: 12px;'>© 2026 Dünya Haber Portalı | Tüm hakları saklıdır. İçerikler küresel RSS kaynaklarından anlık olarak derlenmektedir.</p>",
    unsafe_allow_html=True
)
