import openai

def get_completion(prompt, model="gpt-3.5-turbo"):
    openai.api_key = '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'
    messages = [{"role": "user", "content": prompt}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=0, # this is the degree of randomness of the model's output
    )
    return response.choices[0].message["content"]
def get_openai_response(user_input):
    prompt = f"""
        calculate calories and macronutrients of the following ingredients into the triple backquotes:
        ```{user_input}```
        Write in the csv format: quantity,measurement,ingredient,carbs,fats,proteins,net_carbs,fiber,kcal.
        Examples: 1 large banana
        qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal
        1,large,banana,27,0.4,1.3,23.9,3.1,121
        """
    return get_completion(prompt)