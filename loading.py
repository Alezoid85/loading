import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Ale Load Planner 3D", layout="wide")

# Stile personalizzato: Bianco e Blu ISP
st.markdown("""
    <style>
    .stApp { background-color: white; }
    h1, h2, h3, p, label, span { color: #002D62 !important; }
    .stTextArea textarea { 
        background-color: #f0f2f6 !important; 
        border: 1px solid #002D62 !important; 
        color: #002D62 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #f8f9fa !important;
        border: 1px solid #002D62 !important;
        border-radius: 10px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- TITOLO E ISTRUZIONI ---
st.title("🚚 Ale Load Planner - 3D Stats")
st.write("Incolla le colonne da Excel nel seguente ordine: **ID**, **Lunghezza**, **Larghezza**, **Altezza** (tutte in cm).")

# --- SIDEBAR: PARAMETRI MEZZO ---
st.sidebar.header("⚙️ Dimensioni Mezzo")
camion_L = st.sidebar.number_input("Lunghezza Pianale (cm)", value=1360, help="Standard Bilico: 1360cm")
camion_W = st.sidebar.number_input("Larghezza Pianale (cm)", value=245, help="Standard: 245cm")
camion_H = st.sidebar.number_input("Altezza Massima (cm)", value=270, help="Altezza sotto centina")

# --- AREA DI INPUT ---
data_input = st.text_area(
    "Incolla qui i dati (senza intestazioni)", 
    height=250, 
    placeholder="Cassa_01  120  80  150\nCassa_02  240  100  220..."
)

if data_input:
    try:
        # Caricamento dati incollati
        df = pd.read_csv(
            io.StringIO(data_input), 
            sep=None, 
            names=['ID', 'Lunghezza', 'Larghezza', 'Altezza'], 
            engine='python'
        )
        
        if not df.empty:
            # Algoritmo di calcolo (ordinamento per lunghezza per ottimizzare LDM)
            df = df.sort_values(by='Lunghezza', ascending=False)
            
            posizioni = []
            current_x, current_y, max_h_in_row, metri_lineari = 0, 0, 0, 0
            volume_merce_totale = 0
            errori_altezza = []

            for i, row in df.iterrows():
                l_c = float(row['Lunghezza'])
                w_c = float(row['Larghezza'])
                h_c = float(row['Altezza'])
                
                # Calcolo volume in m3
                volume_merce_totale += (l_c * w_c * h_c) / 1000000

                # Check fuori sagoma
                if h_c > camion_H:
                    errori_altezza.append(f"⚠️ Il collo **{row['ID']}** supera l'altezza del camion ({h_c} cm)!")

                # Logica di posizionamento a terra (Tetris 2D)
                if current_x + w_c > camion_W:
                    current_x = 0
                    current_y += max_h_in_row
                    max_h_in_row = 0
                
                posizioni.append({
                    'ID': row['ID'], 
                    'x0': current_x, 'y0': current_y,
                    'x1': current_x + w_c, 'y1': current_y + l_c,
                    'w': w_c, 'l': l_c, 'h': h_c
                })
                
                current_x += w_c
                max_h_in_row = max(max_h_in_row, l_c)
                metri_lineari = max(metri_lineari, current_y + max_h_in_row)

            # --- GRAFICO PLANIMETRIA ---
            fig = go.Figure()

            # Disegno perimetro camion
            fig.add_shape(type="rect", x0=0, y0=0, x1=camion_W, y1=camion_L,
                          line=dict(color="#002D62", width=4), fillcolor="rgba(0,0,0,0)")

            # Disegno singoli colli
            for p in posizioni:
                # Colore: Pistacchio se OK, Rosso se fuori altezza
                colore_collo = "#D4E157" if p['h'] <= camion_H else "#FF4B4B"
                
                fig.add_shape(type="rect", x0=p['x0'], y0=p['y0'], x1=p['x1'], y1=p['y1'],
                              line=dict(color="#002D62", width=1), fillcolor=colore_collo, opacity=0.8)
                
                # Testo sopra il collo
                fig.add_trace(go.Scatter(
                    x=[(p['x0']+p['x1'])/2], y=[(p['y0']+p['y1'])/2],
                    text=[f"{p['ID']}<br>H:{p['h']}"], 
                    mode="text", textfont=dict(size=10, color="black"), showlegend=False
                ))

            fig.update_layout(
                title="Vista dall'alto del Carico",
                xaxis=dict(range=[-30, camion_W+30], title="Larghezza (cm)"),
                yaxis=dict(range=[-30, camion_L+30], title="Lunghezza (cm)"),
                width=700, height=900, plot_bgcolor='white'
            )

            st.plotly_chart(fig, use_container_width=True)
            
            # --- SEZIONE ERRORI E ALERT ---
            if errori_altezza:
                for err in errori_altezza:
                    st.error(err)

            # --- METRICHE FINALI ---
            st.subheader("📊 Statistiche Carico")
            m1, m2, m3, m4 = st.columns(4)
            
            ldm = metri_lineari / 100
            m1.metric("Metri Lineari (LDM)", f"{ldm:.2f} m")
            
            m2.metric("Volume Merce", f"{volume_merce_totale:.2f} m³")
            
            vol_camion = (camion_L * camion_W * camion_H) / 1000000
            saturazione = (volume_merce_totale / vol_camion) * 100
            m3.metric("Saturazione Vol.", f"{saturazione:.1f}%")
            
            spazio_libero = (camion_L - metri_lineari) / 100
            m4.metric("LDM Liberi", f"{spazio_libero:.2f} m")

    except Exception as e:
        st.error("Errore: controlla che i dati incollati siano 4 colonne numeriche (ID, Lunghezza, Larghezza, Altezza).")
else:
    st.info("💡 Suggerimento: In Excel, seleziona i dati di ID, Lunghezza, Larghezza e Altezza e incollali qui sopra.")