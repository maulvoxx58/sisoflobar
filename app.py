import streamlit as st
import pandas as pd

# Konfigurasi Halaman Web
st.set_page_config(page_title="SISO Performance Dashboard", layout="wide")
st.title("📊 Dashboard Performa SISO")
st.write("Silakan upload file CSV Anda untuk melihat dan memperbarui data dashboard.")

# 1. Fitur Upload File
uploaded_file = st.file_uploader("Upload File CSV Data SISO", type=["csv"])

if uploaded_file:
    # Membaca data, menggunakan separator ';'
    df_raw = pd.read_csv(uploaded_file, sep=";")
    
    # 2. Mengambil tabel lookup untuk Identitas Nama DSE (Kolom AT ke AV / 'MC', 'ID', 'Nama')
    lookup = df_raw[['ID', 'Nama']].dropna(subset=['ID']).drop_duplicates()
    
    # Menggabungkan data utama dengan lookup berdasarkan dse_code dan ID
    df = df_raw.copy()
    df = df.merge(lookup, left_on='dse_code', right_on='ID', how='left')
    
    # Jika nama tidak ditemukan, gunakan kode dse-nya saja
    df['Nama DSE'] = df['Nama'].fillna(df['dse_code'])
    
    # Kolom numerik yang masuk Fokus 1 dan Fokus 2
    numeric_cols = [
        'saldo_mtd', 'sellin_mtd', 'ga_mtd', 
        'tag_n_go_hit', 'biometric_mtd', 'seru_hit', 'cvm_hit'
    ]
    
    # Pembersihan data: Mengubah koma menjadi titik untuk angka desimal
    for col in numeric_cols:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 3. Rename kolom sesuai permintaan
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
    
    st.divider()
    
    # 4. Filter Total berdasarkan Branch
    branches = df['branch'].dropna().unique()
    selected_branch = st.selectbox("🎯 Filter Data Berdasarkan Branch:", ["Semua Branch"] + list(branches))
    
    if selected_branch != "Semua Branch":
        df = df[df['branch'] == selected_branch]

    # --- STATE MANAGEMENT UNTUK FLOW INTERAKSI (DRILL-DOWN) ---
    if 'view_level' not in st.session_state:
        st.session_state.view_level = 'MC' # Pilihan Level: MC, DSE, Outlet
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
        st.subheader("📁 Data Total per Micro Cluster")
        
        # Grouping data
        mc_summary = df.groupby('micro_cluster')[metrics].sum().reset_index()
        
        # Fitur Klik (Pilih MC untuk melihat DSE)
        pilih_mc = st.selectbox("👇 Pilih Micro Cluster untuk melihat detail per-DSE:", ["-- Pilih Micro Cluster --"] + list(mc_summary['micro_cluster']))
        if pilih_mc != "-- Pilih Micro Cluster --":
            st.session_state.view_level = 'DSE'
            st.session_state.selected_mc = pilih_mc
            st.rerun()
            
        st.dataframe(mc_summary, use_container_width=True, hide_index=True)

    # ==========================================
    # LEVEL 2: TAMPILAN DSE
    # ==========================================
    elif st.session_state.view_level == 'DSE':
        st.subheader(f"👤 Data DSE - Micro Cluster: {st.session_state.selected_mc}")
        
        df_mc = df[df['micro_cluster'] == st.session_state.selected_mc]
        dse_summary = df_mc.groupby(['dse_code', 'Nama DSE'])[metrics].sum().reset_index()
        
        # Fitur Klik (Pilih DSE untuk melihat Outlet)
        pilih_dse = st.selectbox("👇 Pilih Nama DSE untuk melihat detail Outlet:", ["-- Pilih DSE --"] + list(dse_summary['Nama DSE']))
        if pilih_dse != "-- Pilih DSE --":
            st.session_state.view_level = 'Outlet'
            st.session_state.selected_dse = pilih_dse
            st.rerun()
            
        st.dataframe(dse_summary, use_container_width=True, hide_index=True)

    # ==========================================
    # LEVEL 3: TAMPILAN OUTLET
    # ==========================================
    elif st.session_state.view_level == 'Outlet':
        st.subheader(f"🏪 Data Outlet - DSE: {st.session_state.selected_dse}")
        
        df_outlet = df[(df['micro_cluster'] == st.session_state.selected_mc) & (df['Nama DSE'] == st.session_state.selected_dse)]
        
        # Tampilkan kolom nama outlet dan metrik fokus 1 & 2
        show_cols = ['outlet_name'] + metrics
        df_show = df_outlet[show_cols].copy()
        
        # Fungsi mengubah warna angka SALDO menjadi merah jika di bawah 10.000
        def color_saldo(val):
            try:
                color = '#ff4b4b' if float(val) < 10000 else '' 
            except:
                color = ''
            return f'color: {color}'
            
        styled_df = df_show.style.map(color_saldo, subset=['SALDO'])
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)