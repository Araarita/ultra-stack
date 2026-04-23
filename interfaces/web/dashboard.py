import streamlit as st
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path
import time

sys.path.insert(0, "/opt/ultra")

st.set_page_config(
    page_title="Ultra Dashboard",
    page_icon="U",
    layout="wide",
)

st.title("Ultra AI Dashboard")
st.caption(f"Actualizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# Auto-refresh
if st.sidebar.checkbox("Auto-refresh 15s", value=False):
    time.sleep(15)
    st.rerun()

# === SERVICIOS ===
st.header("Servicios")

def check_service(name):
    try:
        r = subprocess.run(["systemctl", "is-active", name], capture_output=True, text=True, timeout=3)
        return r.stdout.strip() == "active"
    except:
        return False

def check_docker(name):
    try:
        r = subprocess.run(["docker", "ps", "--filter", f"name={name}", "--format", "{{.Status}}"],
                           capture_output=True, text=True, timeout=3)
        return "Up" in r.stdout
    except:
        return False

col1, col2, col3, col4 = st.columns(4)
services = [
    ("Ultra Bot", check_service("ultra-bot")),
    ("Letta Docker", check_docker("letta")),
    ("Redis", check_service("redis-server")),
    ("Nexus", check_service("nexus-cortex")),
]
for col, (name, active) in zip([col1, col2, col3, col4], services):
    with col:
        st.metric(name, "Activo" if active else "Inactivo")

# === LLM ROUTER ===
st.header("LLM Router")
try:
    from shared.llm_router.router import get_mode_status, list_all_modes
    status = get_mode_status()
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Modo", f"{status['emoji']} {status['mode']}")
    with c2:
        st.metric("Nivel", status['intelligence'])
    with c3:
        st.metric("Costo", status['avg_cost'])
    
    st.caption(status['description'])
    
    with st.expander("Modelos activos"):
        for task, model in status['models'].items():
            st.code(f"{task}: {model}")
    
    with st.expander("Todos los modos"):
        for m in list_all_modes():
            lock = "LOCK" if m['password_required'] else "    "
            st.write(f"{m['emoji']} {lock} **{m['mode']}** {m['intelligence']}")
            st.caption(m['description'])
except Exception as e:
    st.error(f"Error router: {e}")

# === REPORTES ===
st.header("Reportes")

tab1, tab2 = st.tabs(["Research", "Code"])

with tab1:
    d = Path("/opt/ultra/data/reportes")
    if d.exists():
        files = sorted(d.glob("*.md"), key=os.path.getmtime, reverse=True)
        st.metric("Total", len(files))
        if files:
            sel = st.selectbox("Ver", files, format_func=lambda p: p.name[:50])
            if sel:
                st.markdown(sel.read_text()[:5000])
    else:
        st.info("No hay reportes. Usa /research en Telegram.")

with tab2:
    d = Path("/opt/ultra/data/codigo")
    if d.exists():
        files = sorted(d.glob("*.md"), key=os.path.getmtime, reverse=True)
        st.metric("Total", len(files))
        if files:
            sel = st.selectbox("Ver", files, format_func=lambda p: p.name[:50], key="code")
            if sel:
                st.markdown(sel.read_text()[:5000])
    else:
        st.info("No hay código. Usa /code en Telegram.")

# === LOGS ===
st.header("Logs")

log_tab1, log_tab2 = st.tabs(["Ultra Bot", "Crew activo"])

with log_tab1:
    try:
        logs = subprocess.run(
            ["journalctl", "-u", "ultra-bot", "-n", "30", "--no-pager"],
            capture_output=True, text=True, timeout=5
        )
        st.code(logs.stdout[-3000:], language="log")
    except Exception as e:
        st.error(f"Error: {e}")

with log_tab2:
    p = Path("/tmp/crew_hello.log")
    if p.exists():
        c = p.read_text()
        st.metric("Lineas", c.count("\n"))
        st.code(c[-3000:], language="log")
    else:
        st.info("Sin crew activo")

# === SIDEBAR ===
st.sidebar.header("Acciones")

if st.sidebar.button("Reiniciar bot"):
    subprocess.run(["systemctl", "restart", "ultra-bot"])
    st.sidebar.success("OK")

if st.sidebar.button("Reiniciar Letta"):
    subprocess.run(["docker", "restart", "letta"])
    st.sidebar.success("OK")

if st.sidebar.button("Limpiar Redis cache"):
    subprocess.run(["redis-cli", "FLUSHDB"])
    st.sidebar.success("OK")

st.sidebar.markdown("---")
st.sidebar.caption(f"Ultra Stack")
st.sidebar.caption(datetime.now().strftime("%Y-%m-%d"))
