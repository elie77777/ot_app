import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime

st.title("Overtime Tracker")

# Lista de agentes
agents = ["Eliecid", "David", "Jhordan", "Brayan", "Luis", "Andrés", "Julio"]
agent = st.selectbox("Select Agent", agents)

# Campo de fecha
date = st.date_input("Date", value=datetime.today(), key="date_picker", help="Select a date")

# Función para formatear hora
def format_time_input(key, placeholder="hhmm → 1422"):
    user_input = st.text_input(key, placeholder=placeholder)
    user_input = user_input.replace(":", "").strip()
    if len(user_input) == 4 and user_input.isdigit():
        formatted = f"{user_input[:2]}:{user_input[2:]}"
        try:
            return datetime.strptime(formatted, "%H:%M").time()
        except ValueError:
            st.warning(f"Invalid time: {formatted}")
            return None
    elif len(user_input) == 5 and ":" in user_input:
        try:
            return datetime.strptime(user_input, "%H:%M").time()
        except ValueError:
            st.warning(f"Invalid time: {user_input}")
            return None
    else:
        return None

from_time = format_time_input("From (hhmm or hh:mm)")
to_time = format_time_input("To (hhmm or hh:mm)")
reason = st.text_input("Reason", value="Scheduled OT")

bonus = st.selectbox("+20K Bonus?", ["Yes", "No"])
holiday = st.checkbox("Holiday?")

# Cálculo previo
if from_time and to_time:
    start = datetime.combine(datetime.today(), from_time)
    end = datetime.combine(datetime.today(), to_time)
    diff = end - start
    hours, remainder = divmod(diff.seconds, 3600)
    minutes = remainder // 60
    preview_total = f"{hours}h {minutes}m"
else:
    preview_total = ""

st.write(f"**Preview Total Time:** {preview_total}")

# Guardar registro
if st.button("Submit"):
    if not agent or not from_time or not to_time:
        st.error("All fields are required.")
    else:
        with st.spinner("Saving to Google Sheets..."):
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scope
            )
            client = gspread.authorize(creds)
            sheet = client.open("OT_Records").sheet1

            from_str = from_time.strftime("%H:%M")
            to_str = to_time.strftime("%H:%M")

            sheet.append_row([agent, str(date), from_str, to_str, reason, bonus, holiday, ""])
            last_row = len(sheet.get_all_values())
            formula = f'=IF(OR(C{last_row}="",D{last_row}=""),"",TEXT(D{last_row}-C{last_row},"h \\h\\r m \\m\\i\\n"))'
            sheet.update_acell(f"H{last_row}", formula)

        st.success("✅ Record added successfully.")

# -------------------------------
# FILTRO DE TOTALES CON DEBUG
# -------------------------------
st.header("Filter Total Time by Period")

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=scope
)
client = gspread.authorize(creds)
sheet = client.open("OT_Records").sheet1

# Rango de fechas predefinido
period_option = st.selectbox(
    "Select Time Frame",
    ["Del 06 de Octubre al 02 de Noviembre", "Del 03 de Noviembre al 07 de Diciembre"]
)

if period_option == "Del 06 de Octubre al 02 de Noviembre":
    start_date = datetime(2025, 10, 6)
    end_date = datetime(2025, 11, 2)
else:
    start_date = datetime(2025, 11, 3)
    end_date = datetime(2025, 12, 7)

selected_agent = st.selectbox("Agent Name (Filter)", agents)

st.write(f"🔍 **DEBUG INFO:**")
st.write(f"- Buscando: '{selected_agent}'")
st.write(f"- Periodo: {start_date.date()} al {end_date.date()}")

if st.button("Show Total"):
    try:
        values = sheet.get_all_values()
        headers = values[0]
        data = [dict(zip(headers, row)) for row in values[1:] if len(row) == len(headers)]

        st.write(f"📊 Total de filas en la hoja: {len(data)}")

        total_minutes = 0
        filtered_rows = []

        # Primero, mostrar TODOS los nombres de agentes en la hoja
        unique_agents = set()
        for row in data:
            agent_name = row.get("Agent Name", "").strip()
            if agent_name:
                unique_agents.add(agent_name)
        
        st.write(f"👥 Agentes encontrados en la hoja: {sorted(unique_agents)}")
        st.write("---")
        
        for row in data:
            agent_name = row.get("Agent Name", "").strip()
            
            # Comparación case-insensitive (ignora mayúsculas/minúsculas)
            if agent_name.lower() == selected_agent.lower():
                st.write(f"✅ Encontré a '{agent_name}'")
                
                date_str = row.get("Date", "").strip()
                st.write(f"   - Fecha en la hoja: '{date_str}'")
                
                if not date_str:
                    st.write(f"   ⚠️ Fecha vacía, saltando...")
                    continue
                    
                try:
                    # Intenta distintos formatos
                    if isinstance(date_str, datetime):
                        record_date = date_str
                    else:
                        record_date = datetime.strptime(date_str.split(" ")[0], "%Y-%m-%d")
                    
                    st.write(f"   - Fecha convertida: {record_date.date()}")
                    st.write(f"   - ¿Está en el rango? {start_date <= record_date <= end_date}")
                    
                except ValueError as e:
                    st.write(f"   ❌ Error convirtiendo fecha: {e}")
                    continue

                if start_date <= record_date <= end_date:
                    time_str = row.get("Total Time", "")
                    st.write(f"   ✅ ¡Fecha válida! Total Time: '{time_str}'")
                    
                    if "h" in time_str:
                        parts = time_str.split("h")
                        h = int(parts[0].strip())
                        m = int(parts[1].replace("r", "").replace("m", "").replace("min", "").strip() or 0)
                        total_minutes += h * 60 + m
                    filtered_rows.append(row)

        total_hours = total_minutes // 60
        remaining_minutes = total_minutes % 60

        st.write(f"---")
        if filtered_rows:
            st.subheader(f"Total Time for {selected_agent}: {total_hours}h {remaining_minutes}m")
            st.dataframe(filtered_rows)
        else:
            st.info(f"No records found for {selected_agent} for that period.")

    except Exception as e:
        st.error(f"Error reading sheet: {e}")
        import traceback
        st.code(traceback.format_exc())