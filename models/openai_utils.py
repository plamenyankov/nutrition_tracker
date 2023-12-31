import openai
def cleanup_csv(api_response):
    lines = api_response.strip().split("\n")
    cleaned_lines = []

    expected_columns = 9  # Based on the example you provided.

    for line in lines:
        if len(line.split(",")) == expected_columns:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

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
        Examples 1: 1 large banana, 30g cream cheese, 100g oat flakes, 20g shredded coconut
        qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal
        1,large,banana,27,0.4,1.3,23.9,3.1,121
        30,g,cream cheese,0.7,12.3,1.6,0.7,0,120.4
        100,g,oat flakes,55.1,6.9,14.2,1.2,12.3,364
        20,g,shredded coconut,1.5,12.2,1.2,1.3,0,130
        Example 2: 150g sour cream 20% fat
        qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal
        150,g,sour cream 20% fat,2.1,30,3.6,2.1,0,315
        """
    response = get_completion(prompt)
    print("Raw response:", response)
    cleaned_response = cleanup_csv(response)
    return cleaned_response

# 3 large egg, 1 large banana, 30g cream cheese, 20g shredded coconuts, 10g flax seeds, 10g chia seeds, 150g oat flakes, 10g cocoa powder, 100g erythritol