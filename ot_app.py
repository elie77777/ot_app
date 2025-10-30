import streamlit as st
import gspread
from google.oauth2 import service_account
from datetime import datetime

st.title("Overtime Tracker")

# Lista de agentes
agents = ["Eliecid", "David", "Jhordan", "Brayan", "Luis", "Andrés", "Julio"]
agent = st.selectbox("Select Agent", agents)

# Campo de fecha solo seleccionable desde calendario
date = st.date_input("Date", value=datetime.today(), key="date_picker", help="Select a date from the calendar")

# Formateador automático de hora (acepta hhmm o hh:mm)
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

# Nuevo campo de Bonus y Holiday
bonus = st.selectbox("+20K Bonus?", ["Yes", "No"])
holiday = st.checkbox("Holiday?")

# Cálculo local de previa (sin tocar Sheets)
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

# Guardar solo al presionar Submit
if st.button("Submit"):
    if not agent:
        st.error("Agent is required.")
    elif not from_time or not to_time:
        st.error("Both From and To times are required and must be valid.")
    else:
        with st.spinner("Saving to Google Sheets..."):
            # Autenticación segura desde Streamlit Secrets
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"], scopes=scope
            )
            client = gspread.authorize(creds)
            sheet = client.open("OT_Records").sheet1

            # Formato de hora HH:MM
            from_str = from_time.strftime("%H:%M")
            to_str = to_time.strftime("%H:%M")

            # Insertar fila (agregamos el campo holiday)
            sheet.append_row([agent, str(date), from_str, to_str, reason, bonus, holiday, ""])

            # Obtener última fila
            last_row = len(sheet.get_all_values())

            # Fórmula para cálculo de horas
            formula = f'=IF(OR(C{last_row}="",D{last_row}=""),"",TEXT(D{last_row}-C{last_row},"h \\h\\r m \\m\\i\\n"))'

            # Escribir fórmula en columna H (ahora que Holiday es la columna G)
            sheet.update_acell(f"H{last_row}", formula)

        st.success("✅ Record added. Total time will appear in the sheet.")
