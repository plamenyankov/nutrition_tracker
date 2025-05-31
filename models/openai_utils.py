import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # Load environment variables from .env file
api_key = os.getenv('OPENAI_API_KEY')

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)

def cleanup_csv(api_response):
    lines = api_response.strip().split("\n")
    cleaned_lines = []

    expected_columns = 9  # Based on the example you provided.

    for line in lines:
        if len(line.split(",")) == expected_columns:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines)

def get_completion(prompt, model="gpt-4o"):
    messages = [{"role": "user", "content": prompt}]
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0, # this is the degree of randomness of the model's output
    )
    return response.choices[0].message.content

def get_vision_completion(messages, model="gpt-4o"):
    """Get completion from OpenAI with vision capabilities"""
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        max_tokens=1000
    )
    return response.choices[0].message.content

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

def analyze_meal_image(base64_image):
    """Analyze a meal photo to identify foods and estimate portions"""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """Analyze this meal photo and identify all foods with estimated portions.
                    Calculate calories and macronutrients for each food item.

                    Return the results in this CSV format: qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal

                    Important:
                    - Estimate realistic portion sizes based on visual cues in the photo
                    - Include all visible foods and ingredients
                    - Be specific about preparation methods (grilled, fried, etc.)
                    - Use standard units (g, oz, cups, pieces, etc.)

                    Example output:
                    qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal
                    150,g,grilled chicken breast,0,3.6,31,0,0,165
                    200,g,steamed broccoli,14,0.8,5.6,8,6,56"""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ]

    response = get_vision_completion(messages)
    print("Raw meal photo response:", response)
    cleaned_response = cleanup_csv(response)
    return cleaned_response

def analyze_nutrition_label(base64_image, food_name):
    """Analyze a nutrition label photo with provided food name"""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": f"""Extract nutrition information from this nutrition facts label for: {food_name}

                    Read the serving size and nutrition facts from the label.
                    Convert the information to this CSV format: qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal

                    Important:
                    - Use the serving size shown on the label
                    - Extract total carbohydrates, fats, protein, fiber, and calories
                    - Calculate net carbs as (total carbs - fiber)
                    - Use the exact values from the label

                    The food name is: {food_name}

                    Example output:
                    qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal
                    28,g,{food_name},15,2,3,12,3,90"""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                }
            ]
        }
    ]

    response = get_vision_completion(messages)
    print("Raw nutrition label response:", response)
    cleaned_response = cleanup_csv(response)
    return cleaned_response

def analyze_product_images(nutrition_base64, front_base64):
    """Analyze product using both nutrition label and front label photos"""
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": """Analyze these two product photos:
                    1. First photo: Nutrition facts label
                    2. Second photo: Product front showing name and brand

                    Extract the product name and brand from the front photo.
                    Extract nutrition information from the nutrition facts label.

                    Return the results in this CSV format: qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal

                    Important:
                    - Use the serving size from the nutrition label
                    - Include the full product name with brand
                    - Extract exact values from the nutrition facts
                    - Calculate net carbs as (total carbs - fiber)

                    Example output:
                    qty,unit,ingr,carbs,fats,protein,net_carbs,fiber,kcal
                    45,g,Nature Valley Crunchy Granola Bars,29,7,3,26,3,190"""
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{nutrition_base64}",
                        "detail": "high"
                    }
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{front_base64}",
                        "detail": "high"
                    }
                }
            ]
        }
    ]

    response = get_vision_completion(messages, model="gpt-4o")
    print("Raw product photos response:", response)
    cleaned_response = cleanup_csv(response)
    return cleaned_response

# 3 large egg, 1 large banana, 30g cream cheese, 20g shredded coconuts, 10g flax seeds, 10g chia seeds, 150g oat flakes, 10g cocoa powder, 100g erythritol
