import streamlit as st
import sys, os
sys.path.append(r"C:\Users\celin\OneDrive\Documents\Work-Cirrusgo\Ai Eng Task1-Chatbot")

from chatbot_backend import ask_chatbot

st.set_page_config(page_title="Financial Chatbot", layout="wide")

st.title("🤖 Financial Analytics Chatbot")
st.write("Ask questions about budgets, projects, sectors, and procurements.")

# Sidebar for options
with st.sidebar:
    st.header("Options")
    language = st.selectbox("Language", ["Arabic", "English", "Chinese"])
    view_example = st.selectbox("Example View", ["v_projects_with_remaining_budget",
                                                 "v_budget_by_sector",
                                                 "v_procurement_activity_by_sector"])

# Input
user_question = st.text_input("Type your question here:")

# Simulated response
if st.button("Ask"):
    if user_question.strip() == "":
        st.warning("Please type a question first.")
    else:
        st.info("Query sent to AI model...")
        # Mock Claude output
        mock_output = {
            "view": view_example,
            "filters": {
                "department_name": "Internal Audit",
                "sector": "Board"
            }
        }
        st.subheader("Raw Claude JSON Output")
        st.json(mock_output)

        st.subheader("Polished Response")
        st.write(f"AI determined that the relevant view is **{mock_output['view']}**.")
        st.write(f"Applied filters: {mock_output['filters']}")
        st.write("Here you would see the final results from the database.")
