# app.py

import streamlit as st
import pandas as pd
import plotly.express as px


# Function to interact with OpenAI (dummy function; replace with actual API call)
def get_openai_response(prompt):
    # Here you would make an API call to OpenAI
    # For this scaffold, we'll return a dummy response
    return "date, food, carbs, fats, protein, kcal\n2023-10-24, banana, 27, 0.4, 1.3, 121"


# Start of the Streamlit app
st.title("Nutrition Tracker with OpenAI")

# Text area for user to input the list of foods consumed
user_input = st.text_area("Enter the list of foods consumed:")

if st.button("Preview"):
    response = get_openai_response(user_input)
    st.text_area("Preview OpenAI Response:", value=response)

    if st.button("Approve"):
        # Convert the response to a DataFrame and save to a CSV
        df_response = pd.read_csv(pd.StringIO(response))
        # Append to existing CSV or create a new one
        try:
            df_master = pd.read_csv('data.csv')
            df_master = pd.concat([df_master, df_response], ignore_index=True)
        except FileNotFoundError:
            df_master = df_response

        df_master.to_csv('data.csv', index=False)
        st.success("Data saved!")

# Visualize data
st.subheader("Macronutrient Visualization")
try:
    df = pd.read_csv('data.csv')
    # Grouping and summarizing data
    summary = df.groupby('date').sum()
    fig = px.bar(summary, x=summary.index, y="kcal", title="Calories Consumed Over Time")
    st.plotly_chart(fig)
except FileNotFoundError:
    st.write("No data available for visualization.")

