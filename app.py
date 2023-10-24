from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, World!"

if __name__ == '__main__':
    app.run()




# # app.py
#
# import streamlit as st
# import pandas as pd
# import plotly.express as px
# import openai
# from io import StringIO
#
# openai.api_key = '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'
# # Check if the session state properties exist. If not, initialize them.
# if 'df_response' not in st.session_state:
#     st.session_state.df_response = False
# if 'saved' not in st.session_state:
#     st.session_state.saved = False
# # Function to interact with OpenAI (dummy function; replace with actual API call)
# def get_completion(prompt, model="gpt-3.5-turbo"):
#     messages = [{"role": "user", "content": prompt}]
#     response = openai.ChatCompletion.create(
#         model=model,
#         messages=messages,
#         temperature=0.2, # this is the degree of randomness of the model's output
#     )
#     return response.choices[0].message["content"]
#
# def get_openai_response(user_input):
#     return 'qty, unit, ingr, carbs, fats, protein, kcal\n1, large, banana, 27, 0.4, 1.3, 121\n100, gr, oats, 66, 8, 17, 389\n1, large, egg, 0.6, 5, 6, 78\n20, gr, cocoa powder, 3.6, 1.8, 2.2, 98\n100, ml, milk, 4.8, 3.4, 3.3, 60'
#     # prompt = f"""
#     #     calculate calories and macronutrients of the following recipe into the triple backquotes:
#     #     ```{user_input}```
#     #     Write in the csv format: quantity,measurement, ingredient, carbs, fats, proteins, kcal.
#     #     Examples: 1 large banana
#     #     qty, unit, ingr, carbs, fats, protein, kcal
#     #     1, large, banana, 27, 0.4, 1.3, 121
#     #     """
#     # return get_completion(prompt)
# # @st.cache_data
# def load_data(file_name):
#     return pd.read_csv(file_name)
#
# # Start of the Streamlit app
# st.title("Nutrition Tracker with OpenAI")
# df_master = load_data('data.csv')
# st.dataframe(df_master)
#
# # Text area for user to input the list of foods consumed
# user_input = st.text_area("Enter the list of foods consumed:")
#
# if st.button("Preview"):
#     response = get_openai_response(user_input)
#     st.subheader("Preview OpenAI Response:")
#     # Use StringIO to simulate a file object
#     data_io = StringIO(response)
#
#     # Read the data into a pandas DataFrame
#     df_response = pd.read_csv(data_io)
#     df_response.to_csv('data2.csv', index=False)
#     st.success("Data saved!")
#     st.session_state.df_response = True
# if st.session_state.df_response:
#     if st.session_state.saved != True:
#         df = load_data('data2.csv')
#         st.dataframe(df)
#     if st.button("Approve"):
#         try:
#             df = load_data('data2.csv')
#             df_master = load_data('data.csv')
#             df_master = pd.concat([df_master, df], ignore_index=True)
#             st.dataframe(df_master)
#             st.session_state.saved = True
#         except Exception as e:
#             print(e)
#             st.error(f"An error occurred: {e}")
#
#     # if st.button("Approve") and st.session_state.df_response is not None:
#     #     st.session_state.df_response.to_csv('data2.csv', index=False)
#     #     df = pd.read_csv('data2.csv')
#     #     st.dataframe(df)
#     #     st.success("Data saved!")
#         # Convert the response to a DataFrame and save to a CSV
#         # df_response = pd.read_csv(pd.StringIO(response))
#         # Append to existing CSV or create a new one
#         # try:
#         # df_master = pd.read_csv('data.csv')
#         # df_master = pd.concat([df_master, df_response], ignore_index=True)
#         # st.dataframe(df_master)
#         # except FileNotFoundError:
#         #     df_master = df_response
#
#         # df_master.to_csv('data.csv', index=False)
#
#
# # Visualize data
# st.subheader("Macronutrient Visualization")
# # try:
# #     df = pd.read_csv('data.csv')
# #     # Grouping and summarizing data
# #     summary = df.groupby('date').sum()
# #     fig = px.bar(summary, x=summary.index, y="kcal", title="Calories Consumed Over Time")
# #     st.plotly_chart(fig)
# # except FileNotFoundError:
# #     st.write("No data available for visualization.")
#
