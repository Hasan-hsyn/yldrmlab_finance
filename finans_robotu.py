import streamlit as st
import yfinance as yf
import pandas as pd
import streamlit.components.v1 as components

# --- SAYFA AYARLARI (LOGO VE BAŞLIK) ---
st.set_page_config(page_title="YıldırımLab Finance AI", layout="wide", page_icon="⚡")

# --- 1. FONKSİYON: TRADINGVIEW WIDGET (GÖRSEL MOTOR) ---
def tradingview_chart(symbol):
    html_code = f"""
    <div class="tradingview-widget-container">
      <div id="tradingview_12345"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
      <script type="text/javascript">
      new TradingView.widget(
      {{
        "width": "100%",
        "height": 550,
        "symbol": "{symbol}",
        "interval": "D",
        "timezone": "Europe/Istanbul",
        "theme": "dark",
        "style": "1",
        "locale": "tr",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingview_12345",
        "studies": [
          "RSI@tv-basicstudies",
          "MACD@tv-basicstudies",
          "BB@tv-basicstudies",
          "MASimple@tv-basicstudies"
        ]
      }}
      );
      </script>
    </div>
    """
    components.html(html_code, height=550)

# --- 2. FONKSİYON: ANALİZ MOTORU (HESAPLAMA) ---
@st.cache_data(ttl=300)
def veri_getir_ve_hesapla(sembol_bilgisi):
    try:
        # Sentetik Varlık (Gram Altın/Gümüş vb.)
        if sembol_bilgisi["tip"] == "sentetik":
            df_ons = yf.download(sembol_bilgisi["y_ons"], period="2y", progress=False)
            df_kur = yf.download(sembol_bilgisi["y_kur"], period="2y", progress=False)
            
            if df_ons.empty or df_kur.empty: return None
            
            # Sütun Temizliği
            if isinstance(df_ons.columns, pd.MultiIndex): df_ons.columns = df_ons.columns.get_level_values(0)
            if isinstance(df_kur.columns, pd.MultiIndex): df_kur.columns = df_kur.columns.get_level_values(0)
            
            # Formül: (Ons * Dolar) / 31.1035 = Gram TL
            df = pd.DataFrame()
            df['Close'] = (df_ons['Close'] * df_kur['Close']) / 31.1035
            df['High'] = (df_ons['High'] * df_kur['High']) / 31.1035
            df['Low'] = (df_ons['Low'] * df_kur['Low']) / 31.1035
            df['Volume'] = df_kur['Volume'] # Hacim verisi kurdan alınır (Referans)
            
        else:
            # Standart Varlık
            df = yf.download(sembol_bilgisi["y"], period="2y", progress=False)
            if df.empty: return None
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # --- İNDİKATÖRLER ---
        # 1. RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        df['RSI_SMA'] = df['RSI'].rolling(window=14).mean()

        # 2. MACD
        exp12 = df['Close'].ewm(span=12, adjust=False).mean()
        exp26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp12 - exp26
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

        # 3. Bollinger & Sıkışma
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Upper'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower'] = df['SMA20'] - (df['STD20'] * 2)
        df['Band_Width'] = (df['Upper'] - df['Lower']) / df['SMA20']

        # 4. Trend Ortalamaları
        df['SMA50'] = df['Close'].rolling(window=50).mean()
        df['SMA200'] = df['Close'].rolling(window=200).mean()
        
        # 5. Hacim Ortalaması
        if 'Volume' in df.columns:
            df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
        else:
            df['Vol_SMA'] = 0
            
        return df

    except Exception as e:
        return None

# --- 3. FIBONACCI ---
def fibonacci_seviyeleri(df):
    max_fiyat = df['High'].max()
    min_fiyat = df['Low'].min()
    fark = max_fiyat - min_fiyat
    return {
        "0.382": max_fiyat - (fark * 0.382),
        "0.5": max_fiyat - (fark * 0.5),
        "0.618": max_fiyat - (fark * 0.618)
    }

# --- ARAYÜZ YAPISI ---
st.sidebar.title("YıldırımLab Finance AI")
st.sidebar.caption("Yapay Zeka Destekli Finansal Durum Analiz, Yorum Terminali ve Varlık Hesaplama Modeli")

menu = [
    "Canlı Analiz(TradingView) & YıldırımLab Finance AI Yorumu", 
    "Gelişmiş Varlık Hesaplayıcı", 
    "Finans & Emtia Sözlüğü"
]
secim = st.sidebar.radio("Modül Seçiniz:", menu)

# Yasal Uyarı (Sidebar Altı)
st.sidebar.markdown("---")
st.sidebar.warning("""
**YASAL UYARI:**
Bu uygulama eğitim ve analiz amaçlıdır. 
Buradaki veriler yatırım tavsiyesi değildir. 
Veriler Yahoo Finance (15dk Gecikmeli) ve TradingView kaynaklıdır.
""")

# Varlık Listesi (Analiz İçin)
varliklar = {
    "Gram Altın (TL)": {"tv": "FX_IDC:XAUTRYG", "y_ons": "GC=F", "y_kur": "TRY=X", "tip": "sentetik"},
    "Gram Gümüş (TL)": {"tv": "FX_IDC:XAGTRYG", "y_ons": "SI=F", "y_kur": "TRY=X", "tip": "sentetik"},
    "Dolar / TL": {"tv": "FX:USDTRY", "y": "TRY=X", "tip": "normal"},
    "Euro / TL": {"tv": "FX:EURTRY", "y": "EURTRY=X", "tip": "normal"},
    "BIST 100": {"tv": "BIST:XU100", "y": "XU100.IS", "tip": "normal"},
    "Bitcoin ($)": {"tv": "BINANCE:BTCUSD", "y": "BTC-USD", "tip": "normal"},
    "Ethereum ($)": {"tv": "BINANCE:ETHUSD", "y": "ETH-USD", "tip": "normal"},
    "Türk Hava Yolları": {"tv": "BIST:THYAO", "y": "THYAO.IS", "tip": "normal"}
}

# ==============================================================================
# SAYFA 1: ANALİZ VE YAPAY ZEKA YORUMU
# ==============================================================================
if secim == "Canlı Analiz(TradingView) & YıldırımLab Finance AI Yorumu":
    st.title("YıldırımLab Finance AI ⚡")
    st.markdown("**Yapay Zeka(YıldırımLab Finance AI) Destekli Teknik Analiz Raporu**")
    st.warning("⚠️ YASAL UYARI: Veriler Yahoo Finance üzerinden (Gecikmeli) ve TradingView (Anlık) kaynaklarından harmanlanmaktadır. Yatırım tavsiyesi kessinlikle değildir. Burada yapılan yorum ve analiz siyasi/politik haberlerin etkisi dışında matematiksel bir şekilde yapay zeka tarafından yorumlanmaktadır bu verilerden yola çıkılarak yapılan yatırımlardan zarar ederseniz sitemiz sorumlu değildir vesselam.")


    col_sel1, col_sel2 = st.columns([1, 3])
    with col_sel1:
        isim = st.selectbox("İncelenecek Varlık:", list(varliklar.keys()))
    
    secilen = varliklar[isim]

    # 1. TradingView Grafiği
    tradingview_chart(secilen["tv"])

    # 2. AI Raporu
    st.markdown("---")
    st.subheader(f" {isim} İçin YıldırımLab Finance AI Raporu")
    
    with st.spinner("Piyasa verileri, hacim ve volatilite işleniyor..."):
        df = veri_getir_ve_hesapla(secilen)
        
        if df is not None:
            # Son Değerler
            son = df.iloc[-1]
            fib = fibonacci_seviyeleri(df)
            
            # --- Üst Metrikler ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Fiyat", f"{son['Close']:.2f}", help="Yahoo Finance son kapanış fiyatı")
            
            rsi_renk = "off" if son['RSI'] > 70 else "normal" if son['RSI'] < 30 else "off"
            c2.metric("RSI (Güç)", f"{son['RSI']:.1f}", f"Ort: {son['RSI_SMA']:.1f}", delta_color=rsi_renk)
            
            trend = "Yükseliş (Boğa)" if son['Close'] > son['SMA200'] else "Düşüş (Ayı)"
            c3.metric("Ana Trend", trend, f"SMA200: {son['SMA200']:.2f}")
            
            hacim_durumu = "Normal"
            if son['Volume'] > son['Vol_SMA'] * 1.5: hacim_durumu = "🔥 Yüksek"
            elif son['Volume'] < son['Vol_SMA'] * 0.6: hacim_durumu = "💤 Düşük"
            c4.metric("Hacim", hacim_durumu)

            # --- Detaylı Yorum ---
            st.info("YıldırımLab Finance AI Analiz Raporu Detayları:")
            
            col_l, col_r = st.columns(2)
            with col_l:
                st.write("Momentum ve Trend:")
                if son['RSI'] > son['RSI_SMA']: st.write("RSI: Momentum artıyor (Ortalamanın üzerinde).")
                else: st.write("🔻 RSI: Momentum zayıflıyor.")
                
                if son['MACD'] > son['Signal']: st.write("MACD: Pozitif trend sinyali.")
                else: st.write("🔻 MACD: Negatif trend sinyali.")
                
                if son['SMA50'] > son['SMA200']: st.write("🌟 **Golden Cross:** Uzun vade pozitif.")

            with col_r:
                st.write("Volatilite ve Risk:")
                if son['Close'] > son['Upper']: st.write("⚠️ Bollinger: Fiyat tavana çarptı (Direnç).")
                elif son['Close'] < son['Lower']: st.write("Bollinger: Fiyat tabana çarptı (Destek).")
                
                if son['Band_Width'] < 0.10: st.warning("⚠️ Sıkışma: Sert fiyat hareketi yaklaşıyor!")
                else: st.write(" Volatilite normal seviyede.")

            # --- Destekler ---
            st.markdown("---")
            st.write(" Olası Destek Noktaları (Fibonacci):")
            k1, k2, k3 = st.columns(3)
            k1.metric("Destek 1 (%38.2)", f"{fib['0.382']:.2f}")
            k2.metric("Destek 2 (%50.0)", f"{fib['0.5']:.2f}")
            k3.metric("Destek 3 (%61.8)", f"{fib['0.618']:.2f}", delta="Altın Oran", delta_color="normal")
            
        else:
            st.error("Veri alınamadı. Lütfen sayfayı yenileyin veya internet bağlantınızı kontrol edin.")

# ==============================================================================
# SAYFA 2: GELİŞMİŞ HESAPLAYICI (METALLER DAHİL)
# ==============================================================================
elif secim == "Gelişmiş Varlık Hesaplayıcı":
    st.title(" Altın, Gümüş ve Döviz Hesaplayıcı")
    st.markdown("Ons fiyatları ve Dolar kuru üzerinden hesaplanan 'anlık teorik fiyatlardır'.")
    
    if st.button("Piyasayı Güncelle"): st.cache_data.clear()

    @st.cache_data(ttl=300)
    def piyasa_verileri_al():
        try:
            # Tüm verileri tek seferde çekelim
            tickers = ["GC=F", "SI=F", "PL=F", "PA=F", "HG=F", "TRY=X", "EURTRY=X"]
            data = yf.download(tickers, period="1d", progress=False)['Close'].iloc[-1]
            return data
        except: return None

    data = piyasa_verileri_al()
    
    if data is not None:
        # Verileri Değişkenlere Ata
        ons_altin = float(data["GC=F"])
        ons_gumus = float(data["SI=F"])
        ons_platin = float(data["PL=F"])
        ons_paladyum = float(data["PA=F"])
        bakir_lbs = float(data["HG=F"]) # Bakır borsada Lbs (Pound) olarak işlem görür
        usd_try = float(data["TRY=X"])
        eur_try = float(data["EURTRY=X"])
        
        # --- HESAPLAMA MOTORU (TL Bazlı) ---
        # 1 Ons = 31.1035 Gram
        gram_altin = (ons_altin * usd_try) / 31.1035
        gram_gumus = (ons_gumus * usd_try) / 31.1035
        gram_platin = (ons_platin * usd_try) / 31.1035
        gram_paladyum = (ons_paladyum * usd_try) / 31.1035
        
        # Bakır (HG=F) Pound başınadır. 1 Pound = 453.59 Gram. 
        # Kg fiyatını bulmak için: (Fiyat * Dolar) / 0.45359
        kg_bakir = (bakir_lbs * usd_try) / 0.45359

        # Fiyat Listesi
        fiyatlar = {
            " Gram Altın (24K)": gram_altin,
            " Gram Gümüş (Has)": gram_gumus,
            " Gram Platin": gram_platin,
            " Gram Paladyum": gram_paladyum,
            " Kg Bakır (Saf)": kg_bakir,
            " Çeyrek Altın": gram_altin * 1.63,
            " Yarım Altın": gram_altin * 3.26,
            " Tam Altın": gram_altin * 6.52,
            " Dolar ($)": usd_try,
            " Euro (€)": eur_try
        }

        # Ekran Düzeni
        col_tablo, col_hesap = st.columns([1.5, 1])
        
        with col_tablo:
            st.subheader("Anlık Piyasa Fiyatları (TL)")
            df_fiyat = pd.DataFrame(list(fiyatlar.items()), columns=["Varlık", "Birim Fiyat (TL)"])
            # Tabloyu güzelleştir
            st.dataframe(df_fiyat.style.format({"Birim Fiyat (TL)": "{:,.2f} ₺"}), use_container_width=True, hide_index=True)
            st.caption("Bakır fiyatı Kg bazındadır, diğer metaller Gram bazındadır.")

        with col_hesap:
            st.subheader(" Portföy Değeri Hesapla")
            with st.container(border=True):
                secilen_varlik = st.selectbox("Varlık Seç:", list(fiyatlar.keys()))
                adet = st.number_input("Adet / Gram Giriniz:", min_value=0.0, value=1.0, step=0.5)
                
                tutar = fiyatlar[secilen_varlik] * adet
                st.metric("Toplam Tutar", f"{tutar:,.2f} ₺")
                
                if "Altın" in secilen_varlik:
                    st.info(f" {adet} adet {secilen_varlik} yaklaşık ${(tutar/usd_try):,.2f} eder.")

    else:
        st.error("Veri bağlantısı kurulamadı. İnternet bağlantınızı kontrol ediniz.")

# ==============================================================================
# SAYFA 3: FİNANS SÖZLÜĞÜ VE BİLGİ MERKEZİ (YENİLENMİŞ)
# ==============================================================================
elif secim == "Finans & Emtia Sözlüğü":
    st.title(" Finansal Okuryazarlık Merkezi")
    st.markdown("Piyasalarda işlem gören varlıklar ve teknik terimler hakkında hap bilgiler.")

    # 1. SEKME: DEĞERLİ METALLER
    with st.expander(" Değerli Metaller (Altın, Gümüş, Bakır...) Ne İşe Yarar?", expanded=True):
        st.markdown("""
        ###  Altın (Gold)
        * **Nedir?** Dünyanın en eski para birimi ve güvenli limanıdır.
        * **Neden Artar?** Savaş, kriz, enflasyon veya belirsizlik dönemlerinde insanlar paralarını korumak için altına kaçar.
        * **Kullanım:** Mücevher, yatırım, merkez bankası rezervleri.
        
        ###  Gümüş (Silver)
        * **Nedir?** "Fakir adamın altını" olarak bilinir ama sanayide altından daha çok kullanılır.
        * **Kullanım:** Güneş panelleri, elektrikli araçlar, elektronik devreler.
        * **Özellik:** Altına göre fiyatı çok daha hızlı artıp çok daha hızlı düşebilir (Volatilite).
        
        ###  Bakır (Copper)
        * **Lakabı:** "Dr. Bakır" (Doktor Copper).
        * **Neden?** Çünkü bakır fiyatı artıyorsa sanayi çalışıyor, fabrikalar üretim yapıyor demektir. Ekonominin sağlığını gösterir.
        * **Kullanım:** İnşaat, elektrik kabloları, sanayi üretimi.
        
        ###  Platin & Paladyum
        * **Kullanım:** Genellikle otomobillerin egzoz sistemlerinde (Katalitik konvertör) kullanılır.
        * **İlişki:** Otomobil üretimi arttığında bu metallerin fiyatı artar.
        """)

    # 2. SEKME: TEKNİK TERİMLER
    with st.expander(" Teknik Analiz Terimleri (RSI, MACD, Bollinger)"):
        st.markdown("""
        ###  RSI (Göreceli Güç Endeksi)
        * Bir varlığın **"Hız Göstergesi"**dir.
        * **70 Üstü:** Çok hızlı gitti, motor ısındı (Aşırı Alım). Dinlenmesi (Düşüş) gerekebilir.
        * **30 Altı:** Çok yavaşladı, fiyat çok düştü (Aşırı Satım). Tekrar hızlanabilir (Yükseliş).
        
        ###  Bollinger Bantları
        * Fiyatın **"Otobanıdır"**. Fiyat genelde bu şeritlerin içinde gider.
        * **Daralma:** Otoban tek şeride düşerse trafik sıkışır. Sonrasında araçlar (fiyat) aniden hızlanır (Patlama).
        
        ###  Fibonacci Seviyeleri
        * Fiyatın **"Dinlenme Tesisleri"**dir.
        * Düşen bir fiyatın nerede durup soluklanacağını (Destek) matematiksel olarak tahmin eder.
        * **Altın Oran (0.618):** En popüler dinlenme tesisidir.
        
        ###  Golden Cross (Altın Kesişim)
        * 50 günlük ortalamanın (Kısa Vade), 200 günlük ortalamayı (Uzun Vade) yukarı kesmesidir.
        * Anlamı: **"Rüzgar artık arkadan esiyor, uzun yolculuk (yükseliş) başladı."**
        """)

    # 3. SEKME: YASAL BİLGİLENDİRME
    with st.expander(" Yasal Uyarı ve Sorumluluk Reddi"):
        st.warning("""
        Eğitim Amaçlıdır: Bu proje, finansal verileri işleme ve görselleştirme yeteneklerini sergilemek amacıyla geliştirilmiştir.
        Yatırım Tavsiyesi Değildir: Burada üretilen "Al/Sat" sinyalleri veya yorumlar tamamen matematiksel formüllere dayanır. Bir insanın veya kurumun resmi tavsiyesi değildir.
        Risk Uyarısı: Finansal piyasalar risklidir. Paranızı kaybedebilirsiniz. Yatırım kararlarınızı SPK lisanslı danışmanlara danışarak alınız.
        """)