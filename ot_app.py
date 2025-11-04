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

# Función para selector de tiempo estilo despertador
def time_picker(label, key_prefix):
    col1, col2 = st.columns(2)
    with col1:
        hour = st.selectbox(
            f"{label} - Hour",
            options=list(range(0, 24)),
            format_func=lambda x: f"{x:02d}",
            key=f"{key_prefix}_hour"
        )
    with col2:
        minute = st.selectbox(
            f"{label} - Minute",
            options=list(range(0, 60)),
            format_func=lambda x: f"{x:02d}",
            key=f"{key_prefix}_minute"
        )
    return datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time()

# Selectores de tiempo
st.subheader("From Time")
from_time = time_picker("From", "from")

st.subheader("To Time")
to_time = time_picker("To", "to")

reason = st.text_input("Reason", value="Scheduled OT")

bonus = st.selectbox("+20K Bonus?", ["Yes", "No"])
holiday = st.checkbox("Holiday?")
overnight = st.checkbox("Overnight?")

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
    if not agent:
        st.error("Agent is required.")
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

            sheet.append_row([agent, str(date), from_str, to_str, reason, bonus, holiday, overnight, ""])
            last_row = len(sheet.get_all_values())
            formula = f'=IF(OR(C{last_row}="",D{last_row}=""),"",TEXT(D{last_row}-C{last_row},"h \\h\\r m \\m\\i\\n"))'
            sheet.update_acell(f"I{last_row}", formula)

        st.success("✅ Record added successfully.")

# -------------------------------
# FILTRO DE TOTALES
# -------------------------------
st.header("Total Monthly Time")

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

selected_agent = st.selectbox("Agent Name (Filter)", agents, key="filter_agent")

if st.button("Show Total"):
    try:
        values = sheet.get_all_values()
        headers = values[0]
        data = [dict(zip(headers, row)) for row in values[1:] if len(row) == len(headers)]

        total_minutes = 0
        filtered_rows = []

        for row in data:
            agent_name = row.get("Agent Name", "").strip()
            
            # Comparación case-insensitive
            if agent_name.lower() == selected_agent.lower():
                date_str = row.get("Date", "").strip()
                
                if not date_str:
                    continue
                    
                try:
                    if isinstance(date_str, datetime):
                        record_date = date_str
                    else:
                        record_date = datetime.strptime(date_str.split(" ")[0], "%Y-%m-%d")
                except ValueError:
                    continue

                if start_date <= record_date <= end_date:
                    time_str = row.get("Total Time", "").strip()
                    
                    # Parsear diferentes formatos
                    if time_str:
                        try:
                            normalized = time_str.replace(" hr ", "h ").replace(" min", "m")
                            
                            if "h" in normalized:
                                parts = normalized.split("h")
                                h = int(parts[0].strip())
                                
                                if len(parts) > 1:
                                    min_part = parts[1].replace("r", "").replace("m", "").strip()
                                    m = int(min_part) if min_part and min_part.isdigit() else 0
                                else:
                                    m = 0
                                    
                                total_minutes += h * 60 + m
                        except Exception:
                            pass
                            
                    filtered_rows.append(row)

        total_hours = total_minutes // 60
        remaining_minutes = total_minutes % 60

        if filtered_rows:
            st.subheader(f"Total Time for {selected_agent}: {total_hours}h {remaining_minutes}m")
            st.dataframe(filtered_rows)
        else:
            st.info(f"No records found for {selected_agent} for that period.")

    except Exception as e:
        st.error(f"Error reading sheet: {e}")