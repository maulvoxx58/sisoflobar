import streamlit as st
import pandas as pd
import plotly.express as px

# Konfigurasi Halaman Web
st.set_page_config(page_title="SISO Performance Dashboard", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Dashboard Performa SISO")
st.markdown("---")

# 1. Fitur Upload File
with st.sidebar:
    st.header("⚙️ Pengaturan Data")
    uploaded_file = st.file_uploader("Upload File CSV Data SISO", type=["csv"])

if uploaded_file:
    # Membaca data, menggunakan separator ';'
    df_raw = pd.read_csv(uploaded_file, sep=";")
    
    # Mengambil tabel lookup untuk Identitas Nama DSE 
    lookup = df_raw[['ID', 'Nama']].dropna(subset=['ID']).drop_duplicates()
    
    # HAPUS kolom lookup dari data utama agar tidak bentrok
    df = df_raw.drop(columns=['MC', 'ID', 'Nama'], errors='ignore')
    
    # Menggabungkan data utama dengan lookup
    df = df.merge(lookup, left_on='dse_code', right_on='ID', how='left')
    df['Nama DSE'] = df['Nama'].fillna(df['dse_code'])
    
    # Kolom numerik yang masuk Fokus 1 dan Fokus 2
    numeric_cols = [
        'saldo_mtd', 'sellin_mtd', 'ga_mtd', 
        'tag_n_go_hit', 'biometric_mtd', 'seru_hit', 'cvm_hit'
    ]
    
    # Pembersihan data & konversi ke integer agar tidak ada koma (00000)
    for col in numeric_cols:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
    
    # Rename kolom
    rename_cols = {
        'saldo_mtd': 'SALDO',
        'sellin_mtd': 'SP Sellin',
        'ga_mtd': 'GA',
        'tag_n_go_hit': 'Tag n Go',
        'biometric_mtd': 'BIOMETRIC',
        'seru_hit': 'SERU',
        'cvm_hit': 'CVM'
    }
    df = df.rename(columns=rename_cols)
    metrics = list(rename_cols.values())
    
    # Fungsi Formatting Angka Format Indonesia (titik untuk ribuan)
    def format_indo(angka):
        return f"{int(angka):,}".replace(",", ".")

    format_dict = {metric: format_indo for metric in metrics}
    
    # Filter Total berdasarkan Branch
    branches = df['branch'].dropna().unique()
    selected_branch = st.sidebar.selectbox("🎯 Filter Branch:", ["Semua Branch"] + list(branches))
    
    if selected_branch != "Semua Branch":
        df = df[df['branch'] == selected_branch]

    # --- STATE MANAGEMENT ---
    if 'view_level' not in st.session_state:
        st.session_state.view_level = 'MC' 
    if 'selected_mc' not in st.session_state:
        st.session_state.selected_mc = None
    if 'selected_dse' not in st.session_state:
        st.session_state.selected_dse = None

    # Tombol Navigasi
    if st.session_state.view_level != 'MC':
        if st.button("⬅️ Kembali ke Level Sebelumnya"):
            if st.session_state.view_level == 'Outlet':
                st.session_state.view_level = 'DSE'
                st.session_state.selected_dse = None
            else:
                st.session_state.view_level = 'MC'
                st.session_state.selected_mc = None
            st.rerun()

    # ==========================================
    # LEVEL 1: TAMPILAN AWAL (MICRO CLUSTER)
    # ==========================================
    if st.session_state.view_level == 'MC':
        st.header("🏢 Ringkasan Keseluruhan")
        
        # 1. Menampilkan Kartu Total Saldo dan Metrik Utama
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Total Saldo Keseluruhan", format_indo(df['SALDO'].sum()))
        col2.metric("📦 Total SP Sellin", format_indo(df['SP Sellin'].sum()))
        col3.metric("🎯 Total GA", format_indo(df['GA'].sum()))
        col4.metric("📱 Total Tag n Go", format_indo(df['Tag n Go'].sum()))
        
        st.markdown("---")
        
        # Grouping data untuk MC
        mc_summary = df.groupby('micro_cluster')[metrics].sum().reset_index()
        
        # 2. Menampilkan Grafik Perbandingan Antar MC
        st.subheader("📈 Perbandingan Performa antar Micro Cluster")
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            fig_mc_saldo = px.bar(mc_summary, x='micro_cluster', y='SALDO', title="Total Saldo per MC", text_auto='.2s', color='micro_cluster')
            st.plotly_chart(fig_mc_saldo, use_container_width=True)
        with col_chart2:
            fig_mc_sellin = px.bar(mc_summary, x='micro_cluster', y='SP Sellin', title="Total SP Sellin per MC", text_auto='.2s', color='micro_cluster')
            st.plotly_chart(fig_mc_sellin, use_container_width=True)
            
        st.markdown("---")
        
        # Pilihan Drill-down
        col_pilih, _ = st.columns([1, 2])
        with col_pilih:
            pilih_mc = st.selectbox("👇 Buka Detail DSE di Micro Cluster:", ["-- Pilih Micro Cluster --"] + list(mc_summary['micro_cluster']))
            if pilih_mc != "-- Pilih Micro Cluster --":
                st.session_state.view_level = 'DSE'
                st.session_state.selected_mc = pilih_mc
                st.rerun()
                
        st.subheader("🗂️ Tabel Data per Micro Cluster")
        st.dataframe(mc_summary.style.format(format_dict), use_container_width=True, hide_index=True)

    # ==========================================
    # LEVEL 2: TAMPILAN DSE
    # ==========================================
    elif st.session_state.view_level == 'DSE':
        st.header(f"👤 Performa DSE - {st.session_state.selected_mc}")
        
        df_mc = df[df['micro_cluster'] == st.session_state.selected_mc]
        dse_summary = df_mc.groupby(['dse_code', 'Nama DSE'])[metrics].sum().reset_index()
        
        # Kartu Total di Level MC Tersebut
        col1, col2, col3 = st.columns(3)
        col1.metric(f"Total Saldo ({st.session_state.selected_mc})", format_indo(df_mc['SALDO'].sum()))
        col2.metric(f"Total SP Sellin ({st.session_state.selected_mc})", format_indo(df_mc['SP Sellin'].sum()))
        col3.metric(f"Total GA ({st.session_state.selected_mc})", format_indo(df_mc['GA'].sum()))
        
        # Grafik Perbandingan DSE di dalam MC tersebut
        st.subheader(f"📈 Perbandingan Performa DSE di {st.session_state.selected_mc}")
        fig_dse = px.bar(dse_summary, x='Nama DSE', y='SALDO', title="Saldo per DSE", text_auto='.2s', color='Nama DSE')
        st.plotly_chart(fig_dse, use_container_width=True)
        
        st.markdown("---")
        
        # Pilihan Drill-down
        col_pilih, _ = st.columns([1, 2])
        with col_pilih:
            pilih_dse = st.selectbox("👇 Buka Detail Outlet milik DSE:", ["-- Pilih DSE --"] + list(dse_summary['Nama DSE']))
            if pilih_dse != "-- Pilih DSE --":
                st.session_state.view_level = 'Outlet'
                st.session_state.selected_dse = pilih_dse
                st.rerun()
                
        st.subheader("🗂️ Tabel Data per DSE")
        st.dataframe(dse_summary.style.format(format_dict), use_container_width=True, hide_index=True)

    # ==========================================
    # LEVEL 3: TAMPILAN OUTLET
    # ==========================================
    elif st.session_state.view_level == 'Outlet':
        st.header(f"🏪 Detail Outlet - {st.session_state.selected_dse}")
        
        df_outlet = df[(df['micro_cluster'] == st.session_state.selected_mc) & (df['Nama DSE'] == st.session_state.selected_dse)]
        
        # Tampilkan kolom nama outlet dan metrik fokus 1 & 2
        show_cols = ['outlet_code', 'outlet_name'] + metrics
        df_show = df_outlet[show_cols].copy()
        
        # Fungsi styling: Merah jika saldo < 10000
        def highlight_saldo(val):
            try:
                # Karena sebelumnya sudah diubah jadi string berformat titik, kita kembalikan dulu ke integer
                val_int = int(str(val).replace('.', ''))
                return 'color: #ff4b4b; font-weight: bold;' if val_int < 10000 else ''
            except:
                return ''
                
        # Format string (titik) diaplikasikan ke dataframe
        formatted_df = df_show.style.format(format_dict).map(highlight_saldo, subset=['SALDO'])
        
        st.dataframe(formatted_df, use_container_width=True, hide_index=True)

else:
    st.info("👈 Silakan upload file CSV Anda melalui panel di sebelah kiri untuk memunculkan Dashboard.")
