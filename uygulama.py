import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(page_title="KÄPT'N", layout="wide")

st.markdown("""
<style>
    /* Global font büyütme */
    html, body, [class*="css"] {
        font-size: 24px !important;
    }
    /* Metrik kutucukları */
    [data-testid="metric-container"] {
        font-size: 20px !important;
    }
    /* Sidebar */
    [data-testid="stSidebar"] * {
        font-size: 18px !important;
    }
    /* Buton ve inputlar */
    .stNumberInput input, .stSelectbox select {
        font-size: 18px !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("KÄPT'N — Değişiklik Maliyetlendirme Sistemi")

# ── SIDEBAR: PARAMETRELER ────────────────────────────────────────────────────
st.sidebar.header("Parametreler")

st.sidebar.subheader("Zaman Kısıtları")
SOP      = st.sidebar.number_input("SOP - Planlama Ufku (gün)", min_value=1, value=60)
LT       = st.sidebar.number_input("Temin Süresi (LT, gün)", min_value=1, value=10)
MinStock = st.sidebar.number_input("Minimum Stok (MinStock)", min_value=0, value=20)

st.sidebar.subheader("Eski Parça")
I0_old = st.sidebar.number_input("Başlangıç Stoku (I0_old)", min_value=0, value=600)
d_old  = st.sidebar.number_input("Tüketim Hızı (d_old, adet/gün)", min_value=1, value=12)
SS_old = st.sidebar.number_input("Güvenlik Stoğu (SS_old)", min_value=0, value=50)
U_old  = st.sidebar.number_input("Birim Fiyat (U_old, TL)", min_value=0, value=200)
h_old  = st.sidebar.number_input("Tutma Maliyeti (h_old, TL/br/gün)", min_value=0.0, value=1.5)

st.sidebar.subheader("Yeni Parça")
I0_new = st.sidebar.number_input("Başlangıç Stoku (I0_new)", min_value=0, value=300)
h_new  = st.sidebar.number_input("Tutma Maliyeti (h_new, TL/br/gün)", min_value=0.0, value=1.0)

st.sidebar.subheader("İşçilik")
W  = st.sidebar.number_input("Saatlik Ücret (W, TL/saat)", min_value=0, value=35)
Qd = st.sidebar.number_input("Günlük Üretim (Qd, araç/gün)", min_value=1, value=30)

# ── PV MATRİSİ ───────────────────────────────────────────────────────────────
st.subheader("Süreç Tanımları")
st.caption("Her süreç için eski ve yeni parçanın girip girmediğini ve işlem süresini girin.")

default_processes = pd.DataFrame({
    "Süreç":              ["Söküm / Demontaj", "Montaj", "Kalite Kontrol", "Test & Devreye Alma"],
    "Eski Parça Giriyor": [True,  True, True, True],
    "H_old (saat/araç)":  [0.30,  0.50, 0.20, 0.30],
    "Yeni Parça Giriyor": [False, True, True, True],
    "H_new (saat/araç)":  [0.00,  0.30, 0.10, 0.20],
})

process_df = st.data_editor(
    default_processes,
    column_config={
    "Süreç":              st.column_config.TextColumn("Süreç", width="medium"),
    "Eski Parça Giriyor": st.column_config.CheckboxColumn("Eski Parça Bu Sürece Giriyor mu? (PV_old)", width="small"),
    "H_old (saat/araç)":  st.column_config.NumberColumn("Eski Parça İşlem Süresi (H_old, sa/araç)", min_value=0.0, step=0.05, format="%.2f", width="small"),
    "Yeni Parça Giriyor": st.column_config.CheckboxColumn("Yeni Parça Bu Sürece Giriyor mu? (PV_new)", width="small"),
    "H_new (saat/araç)":  st.column_config.NumberColumn("Yeni Parça İşlem Süresi (H_new, sa/araç)", min_value=0.0, step=0.05, format="%.2f", width="small"),
},
    use_container_width=True,
    num_rows="dynamic",
    key="process_table"
)

H_old_total = float((process_df["Eski Parça Giriyor"] * process_df["H_old (saat/araç)"]).sum())
H_new_total = float((process_df["Yeni Parça Giriyor"] * process_df["H_new (saat/araç)"]).sum())

col_info1, col_info2 = st.columns(2)
col_info1.info(f"Eski parça toplam işlem süresi: **{H_old_total:.2f} saat/araç**")
col_info2.info(f"Yeni parça toplam işlem süresi: **{H_new_total:.2f} saat/araç**")

st.divider()

# ── BAĞLI PARÇALAR ───────────────────────────────────────────────────────────
st.subheader("Bağlı Parçalar — Yayılım")
st.caption("Değişiklikten etkilenebilecek bağlı parçaları girin. Satır ekleyip çıkarabilirsiniz.")

default_j = pd.DataFrame({
    "Parça Adı":               ["Bağlı Parça A"],
    "Yayılım Olasılığı DP":    [0.25],
    "Başlangıç Stoku":         [150],
    "Tüketim Hızı (adet/gün)": [4],
    "Güvenlik Stoğu":          [15],
    "Birim Fiyat (TL)":        [180],
    "İşlem Süresi H_j (saat)": [0.30],
})

j_df = st.data_editor(
    default_j,
    column_config={
    "Parça Adı":               st.column_config.TextColumn("Parça Adı", width="medium"),
    "Yayılım Olasılığı DP":    st.column_config.NumberColumn("Yayılım Olasılığı (DP)", min_value=0.0, max_value=1.0, step=0.05, format="%.2f", width="small"),
    "Başlangıç Stoku":         st.column_config.NumberColumn("Başlangıç Stoku (I0_j)", min_value=0, step=10, width="small"),
    "Tüketim Hızı (adet/gün)": st.column_config.NumberColumn("Tüketim Hızı (d_j, adet/gün)", min_value=0, step=1, width="small"),
    "Güvenlik Stoğu":          st.column_config.NumberColumn("Güvenlik Stoğu (SS_j)", min_value=0, step=5, width="small"),
    "Birim Fiyat (TL)":        st.column_config.NumberColumn("Birim Fiyat (U_j, TL)", min_value=0, step=10, width="small"),
    "İşlem Süresi H_j (saat)": st.column_config.NumberColumn("İşlem Süresi (H_j, saat)", min_value=0.0, step=0.05, format="%.2f", width="small"),
},
    use_container_width=True,
    num_rows="dynamic",
    key="j_table"
)

st.divider()

# ── HESAPLAMA ────────────────────────────────────────────────────────────────
def compute(SOP, LT, MinStock, I0_old, d_old, SS_old, U_old, h_old,
            I0_new, h_new, W, Qd, H_old_total, H_new_total, j_df):
    rows = []
    for t in range(1, SOP + 1):

        # MinStock kısıtı
        minstock_ok = True
        for d in range(1, t + 1):
            if max(0, I0_old - d_old * d) < MinStock:
                minstock_ok = False
                break
        if I0_new < MinStock:
            minstock_ok = False

        # C_scrap
        I_old_t = max(0, I0_old - d_old * t)
        C_scrap = max(0, I_old_t - SS_old) * U_old

        # C_inv
        C_inv = 0
        for d in range(1, t):
            C_inv += h_old * max(0, I0_old - d_old * d)
        for d in range(t, SOP + 1):
            C_inv += h_new * I0_new

        # C_labor
        C_labor = Qd * W * ((t - 1) * H_old_total + (SOP - t + 1) * H_new_total)

        # C_prop
        C_prop = 0.0
        for _, j in j_df.iterrows():
            I_j_t   = max(0, j["Başlangıç Stoku"] - j["Tüketim Hızı (adet/gün)"] * t)
            scrap_j = max(0, I_j_t - j["Güvenlik Stoğu"]) * j["Birim Fiyat (TL)"]
            labor_j = j["İşlem Süresi H_j (saat)"] * W
            C_prop += j["Yayılım Olasılığı DP"] * (scrap_j + labor_j)

        TC = C_scrap + C_inv + C_labor + C_prop
        rows.append({
            "t": t, "C_scrap": C_scrap, "C_inv": C_inv,
            "C_labor": C_labor, "C_prop": C_prop, "TC": TC,
            "minstock_ok": minstock_ok
        })
    return pd.DataFrame(rows)

# YENİ — bununla değiştir
if LT > SOP:
    st.error(f"Temin süresi ({LT} gün) SOP'tan ({SOP} gün) büyük olamaz.")
    st.stop()

if j_df.isnull().values.any():
    st.warning("Bağlı parçalar tablosunda boş hücre var. Lütfen tüm alanları doldurun.")
    st.stop()

df = compute(SOP, LT, MinStock, I0_old, d_old, SS_old, U_old, h_old,
             I0_new, h_new, W, Qd, H_old_total, H_new_total, j_df)

# LT ve MinStock kısıtlarını birlikte uygula
valid = df[(df["t"] >= LT) & (df["minstock_ok"] == True)]

opt_var = not valid.empty
if opt_var:
    opt    = valid.loc[valid["TC"].idxmin()]
    worst  = valid.loc[valid["TC"].idxmax()]
    saving = worst["TC"] - opt["TC"]
    opt_t  = int(opt["t"])
    valid_ts = set(valid["t"].tolist())
else:
    opt_t  = -1
    valid_ts = set()

# ── METRİKLER ────────────────────────────────────────────────────────────────
if opt_var:
    st.subheader("Sonuçlar")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Optimal Değişiklik Günü",        f"{int(opt['t'])}. gün")
    c2.metric("Minimum TC",                f"{opt['TC']:,.0f} TL")
    c3.metric("En Kötü Karardan Tasarruf", f"{saving:,.0f} TL")
    c4.metric("Tasarruf Oranı",            f"%{saving / worst['TC'] * 100:.0f}")
else:
    sorunlu = df[df["minstock_ok"] == False]["t"]
    if not sorunlu.empty:
        ilk = int(sorunlu.min())
        st.warning(
            f"Geçerli gün bulunamadı — grafik bilgi amaçlı gösteriliyor. "
            f"Eski stok {ilk}. günde MinStock ({MinStock}) seviyesinin altına düşüyor. "
            f"Başlangıç stokunu artırın, tüketim hızını azaltın veya MinStock değerini düşürün."
        )
    else:
        st.warning("Geçerli gün bulunamadı — grafik bilgi amaçlı gösteriliyor.")

# ── ANA GRAFİK ───────────────────────────────────────────────────────────────
def hex_to_rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def bar_colors(base, df, opt_t, lt, valid_ts):
    colors = []
    for _, row in df.iterrows():
        t = row["t"]
        if t not in valid_ts:
            colors.append(hex_to_rgba(base, 0.15))   # geçersiz (MinStock ihlali)
        elif t < lt:
            colors.append(hex_to_rgba(base, 0.25))   # LT öncesi
        elif t == opt_t:
            colors.append(hex_to_rgba(base, 1.0))    # optimal
        else:
            colors.append(hex_to_rgba(base, 0.75))   # geçerli
    return colors

fig = go.Figure()
fig.add_bar(name="Hurda",      x=df["t"], y=df["C_scrap"],
            marker_color=bar_colors("#C8102E", df, opt_t, LT, valid_ts), offsetgroup=0)
fig.add_bar(name="Stok tutma", x=df["t"], y=df["C_inv"],
            marker_color=bar_colors("#5B8DB8", df, opt_t, LT, valid_ts), offsetgroup=0)
fig.add_bar(name="İşçilik",    x=df["t"], y=df["C_labor"],
            marker_color=bar_colors("#4CAF82", df, opt_t, LT, valid_ts), offsetgroup=0)
fig.add_bar(name="Yayılım",    x=df["t"], y=df["C_prop"],
            marker_color=bar_colors("#E8A838", df, opt_t, LT, valid_ts), offsetgroup=0)
fig.add_scatter(name="TC", x=df["t"], y=df["TC"], mode="lines",
                line=dict(color="rgba(255,255,255,0.4)", width=2, dash="dot"))
fig.update_layout(
    barmode="stack", height=400,
    xaxis_title="Değişiklik günü (t)",
    yaxis_title="Maliyet (TL)",
    legend=dict(orientation="h", y=1.08),
    margin=dict(t=40, b=40),
    annotations=[dict(
        x=opt_t, y=opt["TC"],
        text=f"★ Optimal: {opt_t}. gün",
        showarrow=True, arrowhead=2,
        bgcolor="#C8102E", font=dict(color="white"),
        ax=40, ay=-40
    )]if opt_var else []
)

# Stokun MinStock altına düştüğü ilk günü işaretle
minstock_ihlal = df[df["minstock_ok"] == False]["t"]
if not minstock_ihlal.empty:
    ihlal_gunu = int(minstock_ihlal.min())
    fig.add_vline(
        x=ihlal_gunu,
        line_width=2, line_dash="dash", line_color="#C8102E",
        annotation_text=f"⚠ Stok MinStock altına düşüyor ({ihlal_gunu}. gün)",
        annotation_position="top right",
        annotation_font_color="#C8102E"
    )

st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── DUYARLILIK ANALİZİ ───────────────────────────────────────────────────────
st.subheader("Duyarlılık Analizi")
st.caption("Seçilen parametrenin optimal Değişiklik günü üzerindeki etkisini gösterir.")

SENS_PARAMS = {
    "Temin süresi (LT)":        {"key": "LT",    "range": list(range(1, min(SOP, 45), 3))},
    "Birim fiyat eski parça":   {"key": "U_old", "range": [50, 100, 150, 200, 300, 400, 500, 600]},
    "Eski parça tutma mal.":    {"key": "h_old", "range": [0.2, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]},
    "Günlük üretim hacmi":      {"key": "Qd",    "range": [10, 20, 30, 50, 70, 100, 150, 200]},
    "Yeni parça tutma mal.":    {"key": "h_new", "range": [0.1, 0.3, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]},
    "Eski stok tüketim hızı":   {"key": "d_old", "range": [2, 4, 6, 9, 12, 18, 24, 36, 50]},
}

selected = st.selectbox("Parametre seçin", list(SENS_PARAMS.keys()))
cfg = SENS_PARAMS[selected]

base_params = dict(
    SOP=SOP, LT=LT, MinStock=MinStock,
    I0_old=I0_old, d_old=d_old, SS_old=SS_old, U_old=U_old, h_old=h_old,
    I0_new=I0_new, h_new=h_new, W=W, Qd=Qd,
    H_old_total=H_old_total, H_new_total=H_new_total,
)

sens_x, sens_y = [], []
for val in cfg["range"]:
    p = base_params.copy()
    p[cfg["key"]] = val
    try:
        df_s = compute(p["SOP"], p["LT"], p["MinStock"],
                       p["I0_old"], p["d_old"], p["SS_old"], p["U_old"], p["h_old"],
                       p["I0_new"], p["h_new"], p["W"], p["Qd"],
                       p["H_old_total"], p["H_new_total"], j_df)
        v_s = df_s[(df_s["t"] >= p["LT"]) & (df_s["minstock_ok"] == True)]
        if not v_s.empty:
            sens_x.append(val)
            sens_y.append(int(v_s.loc[v_s["TC"].idxmin(), "t"]))
    except Exception:
        pass

if sens_x:
    fig_s = go.Figure()
    fig_s.add_scatter(
        x=sens_x, y=sens_y, mode="lines+markers",
        line=dict(color="#C8102E", width=2),
        marker=dict(size=8, color="#C8102E")
    )
    fig_s.update_layout(
        height=280,
        xaxis_title=selected,
        yaxis_title="Optimal t (gün)",
        yaxis=dict(range=[0, SOP + 2]),
        margin=dict(t=20, b=40)
    )
    st.plotly_chart(fig_s, use_container_width=True)
else:
    st.warning("Bu parametre aralığında geçerli sonuç bulunamadı.")

# ── SEZGİSEL KARAR KARŞILAŞTIRMASI ──────────────────────────────────────────
st.subheader("Sezgisel Karar Analizi")
st.caption("Modelin önerdiği optimal gün ile sezgisel olarak seçilen günü karşılaştırın.")

if opt_var:
    sez_col1, sez_col2 = st.columns([1, 2])
    with sez_col1:
        sez_t = st.number_input(
            "Sezgisel karar günü",
            min_value=1,
            max_value=SOP,
            value=min(int(opt_t + 10), SOP),
            help="Mühendis modeli kullanmadan hangi günü seçerdi?"
        )

    sez_row = df[df["t"] == sez_t].iloc[0]
    sez_tc  = sez_row["TC"]
    opt_tc  = opt["TC"]
    fark    = sez_tc - opt_tc
    fark_pct = fark / opt_tc * 100 if opt_tc > 0 else 0

    with sez_col2:
        c1, c2, c3 = st.columns(3)
        c1.metric("Sezgisel Karar TC",  f"{sez_tc:,.0f} TL",
                  delta=f"+{fark:,.0f} TL" if fark > 0 else f"{fark:,.0f} TL",
                  delta_color="inverse")
        c2.metric("Optimal Karar TC",   f"{opt_tc:,.0f} TL")
        c3.metric("Fazladan Maliyet",   f"{fark:,.0f} TL",
                  delta=f"%{fark_pct:.1f}" if fark > 0 else f"%{fark_pct:.1f}",
                  delta_color="inverse")

    if fark > 0:
        st.error(
            f"{sez_t}. gün yerine {int(opt_t)}. günde değişiklik yapılsaydı "
            f"**{fark:,.0f} TL** tasarruf edilirdi (%{fark_pct:.1f})."
        )
    elif fark < 0:
        st.warning(
            f"{sez_t}. gün seçimi optimal günden "
            f"**{abs(fark):,.0f} TL** daha ucuz görünüyor — "
            f"ancak bu gün MinStock veya LT kısıtını ihlal ediyor olabilir."
        )
    else:
        st.success(f"{sez_t}. gün zaten optimal gün! Model ve sezgi örtüşüyor.")
else:
    st.info("Geçerli gün bulunamadığından karşılaştırma yapılamıyor.")

st.divider()

# ── DETAY TABLO ──────────────────────────────────────────────────────────────
with st.expander("Tüm günlerin maliyet tablosu"):
    st.markdown(
        "🟩 Optimal gün &nbsp;&nbsp; "
        "🟨 LT öncesi (Değişiklik yapılamaz) &nbsp;&nbsp; "
        "🟥 MinStock ihlali",
        unsafe_allow_html=True
    )

    display = df[["t", "C_scrap", "C_inv", "C_labor", "C_prop", "TC", "minstock_ok"]].copy()
    display.columns = ["Gün (t)", "C_scrap", "C_inv", "C_labor", "C_prop", "TC", "MinStock OK"]
    display = display.set_index("Gün (t)")

    def satir_stili(row):
        styles = []
        for col in row.index:
            t        = row.name
            minstock = df[df["t"] == t]["minstock_ok"].values[0]
            is_opt   = opt_var and t == int(opt["t"])
            if is_opt:
                s = "background-color: rgba(29,158,117,0.35); color: #ffffff; font-weight: bold"
            elif not minstock:
                s = "background-color: rgba(200,16,46,0.20); color: #aaaaaa"
            elif t < LT:
                s = "background-color: rgba(255,200,0,0.10); color: #aaaaaa"
            else:
                s = ""
            styles.append(s)
        return styles

    st.dataframe(
        display.style
               .format({"C_scrap": "{:,.0f}", "C_inv": "{:,.0f}",
                        "C_labor": "{:,.0f}", "C_prop": "{:,.0f}", "TC": "{:,.0f}"})
               .apply(satir_stili, axis=1),
        use_container_width=True
    )
