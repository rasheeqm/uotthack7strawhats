import asyncio
import os
import json
import getpass
from typing import Literal, List
from pydantic import BaseModel, Field

# Replace this with the async-compatible modules in langchain, if available
# If there's no async method available, you can wrap synchronous calls using `asyncio.to_thread`.
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState, StateGraph, START, END
from langgraph.types import Command

# If you plan to use aiofiles for file I/O to avoid blocking, import it
# import aiofiles

# Instead of requests, use httpx for async HTTP calls
import httpx

# If there's no environment variable, request input
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

# Initialize your LLM in an async-friendly way, if possible
llm = ChatOpenAI(model="gpt-4", temperature=0)

class UserProfile(BaseModel):
    age: int
    sex: str
    height: float  # in cm
    weight: float  # in kg
    diet_preference: List[str]
    allergies: List[str]
    activity_level: str
    goal: str
    medical_conditions: List[str]
    budget: float

# ----------------------------------------
# File handling (sync vs. async)
# ----------------------------------------

def extract_json_from_response(content: str) -> str:
    """Extract JSON from triple backtick code blocks or plain text."""
    if content.startswith('```json\n') and content.endswith('\n```'):
        return content[7:-4]
    elif content.startswith('```\n') and content.endswith('\n```'):
        return content[4:-4]
    return content

def ensure_file_exists(filename: str, default_content: dict = None):
    """Create file if it doesn't exist."""
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump(default_content or {}, f)

def safe_read_json(filename: str, default_content: dict = None):
    """Safely read JSON file with fallback to default content."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_content or {}

def safe_write_json(filename: str, content: dict):
    """Safely write content to JSON file."""
    with open(filename, 'w') as f:
        json.dump(content, f, indent=2)

def initialize_files():
    ensure_file_exists('agent1_output.json', {"items": [], "budget": 0})
    ensure_file_exists('item_prices.json', {"items": [], "total_price": 0, "budget": 0})

# ----------------------------------------
# Helper Functions
# ----------------------------------------

def calculate_caloric_needs(profile: UserProfile) -> float:
    """Calculate estimated daily caloric needs based on user profile."""
    # Basic BMR calculation using Harris-Benedict equation
    if profile.sex.lower() == "male":
        bmr = 88.362 + (13.397 * profile.weight) + (4.799 * profile.height) - (5.677 * profile.age)
    else:
        bmr = 447.593 + (9.247 * profile.weight) + (3.098 * profile.height) - (4.330 * profile.age)
    
    # Activity level multipliers
    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "very_active": 1.725,
        "extra_active": 1.9
    }
    
    activity_factor = activity_multipliers.get(profile.activity_level.lower(), 1.2)
    total_calories = bmr * activity_factor
    
    # Adjust based on goal
    if profile.goal.lower() == "weight_loss":
        total_calories *= 0.8
    elif profile.goal.lower() == "weight_gain":
        total_calories *= 1.2
    
    return round(total_calories)

def create_grocery_prompt(profile: UserProfile) -> str:
    calories = calculate_caloric_needs(profile)
    json_structure = '''
{
    "items": [
        {
            "name": "item_name",
            "quantity": "quantity_with_unit"
        }
    ],
    "budget": budget_amount
}
'''
    return f"""You are a personalized grocery list generator. Create a list of grocery items with quantities for one week based on the following user profile:

REMEMBER:
- Age: {profile.age} years
- Sex: {profile.sex}
- Height: {profile.height} cm
- Weight: {profile.weight} kg
- Diet Preferences: {', '.join(profile.diet_preference)}
- Allergies: {', '.join(profile.allergies)}
- Activity Level: {profile.activity_level}
- Goal: {profile.goal}
- Medical Conditions: {', '.join(profile.medical_conditions)}
- Estimated Daily Caloric Needs: {calories} calories
- Weekly Budget: ${profile.budget}

REQUIREMENTS:
1. Ensure NO items from the allergens list are included
2. Follow the dietary preferences strictly
3. Consider medical conditions when selecting items
4. Plan for {calories} calories per day
5. All quantities MUST include units (e.g., "2 lbs", "1 gallon", "500g", "3 pieces")
6. Stay within the weekly budget of ${profile.budget}

The output must be valid JSON with this structure:
{json_structure}"""

def clean_price(price_str):
    """Clean and convert price string to float."""
    if isinstance(price_str, (int, float)):
        return float(price_str)
    if isinstance(price_str, str):
        cleaned = ''.join(char for char in price_str if char.isdigit() or char == '.')
        return float(cleaned) if cleaned else 0.0
    return 0.0

# ----------------------------------------
# Tools and Agents
# ----------------------------------------

async def search_grocery_tracker_async(store_type_value: str, specific_store_value: str, item_names: List[str], out_file: str):
    """
    Example asynchronous search function.
    In your real code, adapt this to do the actual grocery search with async HTTP calls.
    """
    # Pseudo-code or placeholder:
    async with httpx.AsyncClient() as client:
        # Simulate searching or calling some endpoint for each item
        results = {"ingredients": []}
        for item_name in item_names:
            # Some fake call
            # e.g., response = await client.get("https://fake.api/search", params={"q": item_name})
            # data = response.json()
            # For demo, just store a mock result:
            results["ingredients"].append({
                "name": item_name,
                "prices": "$3.99",  # mock
                "price": "$3.99",
                "url": "http://example.com"
            })
        # Save to file
        safe_write_json(out_file, results)

async def load_ingredients_data(item_names: List[str]) -> dict:
    """Load ingredient data (async version)"""
    store_type_value = "nofrills"
    specific_store_value = "3643"
    out_file = "agent1_search_to_cheapest_ingredient.json"
    
    # Perform an asynchronous search
    await search_grocery_tracker_async(store_type_value, specific_store_value, item_names, out_file)
    
    # Synchronously read the file (could also do aiofiles if you wish)
    with open(out_file, 'r') as f:
        return json.load(f)

# Example tool for Price Checker
async def find_cheapest():
    """
    Async version of the price checker tool. Reads the grocery list, finds prices, writes item_prices.json.
    """
    try:
        print("Reading from agent1_output.json...")
        with open('agent1_output.json', 'r') as f:
            grocery_list = json.load(f)

        # Extract names of the items into a list
        item_names = [item['name'] for item in grocery_list['items']]
        print(f"Debug - Items: {item_names}")

        # Load ingredients data asynchronously
        ingredients_data = await load_ingredients_data(item_names)
        ingredients_dict = {
            item['name'].lower(): item
            for item in ingredients_data.get('ingredients', [])
        }

        results = []
        total_price = 0
        
        for item in grocery_list.get('items', []):
            item_name = item['name'].lower()
            
            if item_name in ingredients_dict:
                item_data = ingredients_dict[item_name]
                quantity = item['quantity']
                # Attempt to parse quantity as a float (very naive approach)
                if isinstance(quantity, str):
                    numeric_part = ''.join(filter(str.isdigit, quantity))
                    quantity = float(numeric_part) if numeric_part else 1

                # Calculate cost
                val = float(item_data['prices'].replace("$", ""))  # naive parse
                print(f"Cost of {item_data['name']} is {val}")
                item_total = val  # * quantity, if that applies?

                results.append({
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price': item_data['price'],
                    'total_price': item_total,
                    'url': item_data['url']
                })
                total_price += item_total
            else:
                # Not found in data
                results.append({
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price': None,
                    'total_price': None,
                    'url': None
                })

        output_data = {
            'items': results,
            'total_price': total_price,
            'budget': grocery_list.get('budget', 0)
        }
        safe_write_json('item_prices.json', output_data)
        return output_data

    except Exception as e:
        print(f"Error in find_cheapest: {str(e)}")
        return {"error": str(e)}

# If you have a tool decorator, update it to handle async. 
# This depends on your framework. 
# For illustration, we skip the decorator or do something like:
# @tool
async def find_cheapest_tool():
    return await find_cheapest()

# ----------------------------------------
# Workflow Nodes
# ----------------------------------------

async def grocery_list_node(state: MessagesState) -> Command[Literal["price_checker"]]:
    """Process grocery list generation with user profile considerations."""
    # If your agent has an async invoke method:
    # result = await grocery_list_agent.ainvoke(state)
    # Otherwise, wrap synchronous calls with to_thread:
    result = await asyncio.to_thread(grocery_list_agent.invoke, state)

    try:
        content = result["messages"][-1].content
        cleaned_content = extract_json_from_response(content)
        grocery_list = json.loads(cleaned_content)
        print("Parsed grocery list:", json.dumps(grocery_list, indent=2))
        safe_write_json('agent1_output.json', grocery_list)
        
    except Exception as e:
        print(f"Error in grocery list generation: {e}")
        # On error, still go to price_checker
        return Command(update={"messages": result["messages"]}, goto="price_checker")
    
    # Convert last message to a HumanMessage
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="grocery_list_generator"
    )
    
    return Command(
        update={"messages": result["messages"]},
        goto="price_checker"
    )

async def price_checker_node(state: MessagesState) -> MessagesState:
    """Check prices and update the state."""
    # If your REACT agent has an async method:
    # result = await price_checker_agent.ainvoke(state)
    # or wrap with to_thread:
    result = await asyncio.to_thread(price_checker_agent.invoke, state)
    
    prices_data = safe_read_json('item_prices.json')
    print(f"Debug - Price checker result: {json.dumps(prices_data, indent=2)}")

    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="price_checker"
    )
    return result

def route_by_budget(state: MessagesState) -> Literal["grocery_list_generator", "recipe_generator", "end"]:
    """Route based on budget comparison (sync is typically fine)."""
    try:
        prices_data = safe_read_json('item_prices.json')
        print("Debug - Loaded prices data:", json.dumps(prices_data, indent=2))
        
        total_price = clean_price(prices_data.get('total_price', 0))
        budget = clean_price(prices_data.get('budget', 0))
        budget_threshold = budget * 1.10
        
        print(f"Debug - Total Price: ${total_price}")
        print(f"Debug - Budget: ${budget}")
        print(f"Debug - Budget Threshold: ${budget_threshold}")
        
        if total_price <= budget_threshold:
            print("Debug - Routing to recipe_generator")
            return "recipe_generator"
        
        # Over budget logic
        items = prices_data.get('items', [])
        valid_items = []
        for item in items:
            try:
                price = clean_price(item.get('price'))
                if price > 0:
                    item['price'] = price
                    valid_items.append(item)
            except (TypeError, ValueError):
                continue
                
        if valid_items:
            most_expensive = max(valid_items, key=lambda x: x['price'])
            if 'messages' not in state:
                state['messages'] = []
            state['messages'].append(
                HumanMessage(
                    content=f"The total price ${total_price:.2f} is over budget threshold "
                            f"(${budget_threshold:.2f}). Please replace {most_expensive['name']} "
                            f"(${most_expensive['price']:.2f}/unit) with a cheaper alternative.",
                    name="budget_router"
                )
            )
            print("Debug - Routing back to grocery_list_generator due to over budget")
            return "grocery_list_generator"
            
    except Exception as e:
        print(f"Error in route_by_budget: {e}")
        return "end"

async def recipe_generator_node(state: MessagesState) -> MessagesState:
    """Generate recipes based on available ingredients and user profile."""
    # Example: use httpx.AsyncClient for your external calls
    global token  # if needed

    # 1) Post your grocery data
    try:
        async with httpx.AsyncClient() as client:
            with open('item_prices.json', 'r') as file:
                data = json.load(file)
                groceries = [
                    {"ingredient_name": item["name"],
                     "price": item["total_price"],
                     "quantity": item["quantity"]}
                    for item in data['items']
                ]
            data_for_api = {"groceries": groceries}

            # Make the POST request to get nutrition data
            response = await client.post(
                "http://127.0.0.1:8000/grocery/grocery-list",
                json=data_for_api,
                headers={'Authorization': f"Bearer {token}"}
            )
            response.raise_for_status()
    except httpx.RequestError as e:
        print(f"Error during grocery API call: {e}")

    # 2) Post your recipe data
    try:
        async with httpx.AsyncClient() as client:
            with open('/Users/rohitshelke/Desktop/Work/Projects/uotthack7strawhats/meals.json', 'r') as file:
                data = json.load(file)
            recipes_list = data.get("recipes", [])
            for recipe in recipes_list:
                response = await client.post(
                    "http://127.0.0.1:8000/meals/meal",
                    json=recipe,
                    headers={'Authorization': f"Bearer {token}"}
                )
                response.raise_for_status()
    except httpx.RequestError as e:
        print(f"Error during meals API call: {e}")

    # 3) Generate new recipes with the LLM
    try:
        with open('item_prices.json', 'r') as f:
            price_data = json.load(f)
        ingredients = [item['name'] for item in price_data.get('items', [])]
        
        print("Debug - Available ingredients:", ingredients)
        prompt = create_recipe_prompt(current_profile, ingredients)
        
        # If there's an async version:
        recipe_agent = create_react_agent(
            llm,
            tools=[],
            state_modifier=(
                "You are a recipe generator that creates structured JSON output. "
                "Always ensure your output is valid JSON with all property names in double quotes. "
                f"Your task: {prompt}"
            )
        )
        
        # Add the request to the state
        if 'messages' not in state:
            state['messages'] = []
        state['messages'].append(
            HumanMessage(content="Generate recipes based on the provided ingredients and requirements.")
        )
        
        # result = await recipe_agent.ainvoke(state)  # if async is supported
        result = await asyncio.to_thread(recipe_agent.invoke, state)  # fallback if not
        
        print("Debug - Recipe agent raw output:", result["messages"][-1].content)
        content = result["messages"][-1].content
        cleaned_content = extract_json_from_response(content)
        
        try:
            recipes = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            recipes = {"recipes": [], "error": "Failed to generate valid recipes"}
        
        print("Debug - Parsed recipes:", json.dumps(recipes, indent=2))
        safe_write_json('meals.json', recipes)

        result["messages"][-1] = HumanMessage(
            content=json.dumps(recipes, indent=2),
            name="recipe_generator"
        )
        return result
    
    except Exception as e:
        print(f"Error in recipe generation: {e}")
        return state

def create_recipe_prompt(profile: UserProfile, ingredients: list) -> str:
    return f"""Generate 7 recipes based on these ingredients and user profile. Return ONLY valid JSON.

Profile:
- Age: {profile.age}
- Diet Preferences: {', '.join(profile.diet_preference)}
- Allergies: {', '.join(profile.allergies)}
- Medical Conditions: {', '.join(profile.medical_conditions)}
- Goal: {profile.goal}
Available Ingredients: {', '.join(ingredients)}

Requirements:
1. Only use the available ingredients
2. Respect dietary restrictions and allergies
3. Create recipes suitable for the user's medical conditions
4. Include detailed nutritional information

Your response must be ONLY the following JSON structure, with no additional text:
{{
    "recipes": [
        {{
            "meal_name": "Name of the meal",
            "ingredients": [
                {{
                    "item": "ingredient name",
                    "quantity": "amount with units"
                }}
            ],
            "instructions": [
                "Step 1",
                "Step 2"
            ],
            "nutritional_info": {{
                "protein": "X grams",
                "carbs": "Y grams",
                "fat": "Z grams",
                "calories": "Number in kcal"
            }}
        }}
    ]
}}"""

# ----------------------------------------
# Main Async Workflow
# ----------------------------------------

async def run_grocery_workflow(profile: UserProfile, jwt_token: str, user_message: str) -> str:
    """Run the grocery list workflow with user profile, asynchronously."""
    initialize_files()
    
    # Store profile globally for recipe generation
    global current_profile
    global token
    token = jwt_token
    current_profile = profile
    
    # Create grocery list agent (async if possible)
    global grocery_list_agent
    grocery_list_agent = create_react_agent(
        llm,
        tools=[],  # no tools used here
        state_modifier=create_grocery_prompt(profile)
    )
    
    # Similarly for the price checker agent
    global price_checker_agent
    price_checker_agent = create_react_agent(
        llm,
        tools=[find_cheapest_tool],  # our async tool
        state_modifier="You check prices and suggest substitutions if over budget."
    )
    
    initial_state = {
        "messages": [
            HumanMessage(content=user_message or "Generate a personalized grocery list.")
        ]
    }

    # Build the state graph
    workflow = StateGraph(MessagesState)
    workflow.add_node("grocery_list_generator", grocery_list_node)
    workflow.add_node("price_checker", price_checker_node)
    workflow.add_node("recipe_generator", recipe_generator_node)

    workflow.add_edge(START, "grocery_list_generator")
    workflow.add_edge("grocery_list_generator", "price_checker")
    workflow.add_edge("recipe_generator", END)
    workflow.add_conditional_edges(
        "price_checker",
        route_by_budget,
        {
            "grocery_list_generator": "grocery_list_generator",
            "recipe_generator": "recipe_generator",
            "end": END
        }
    )
    graph = workflow.compile()

    # Because langgraph’s graph streaming might be sync-only,
    # you can wrap it in `asyncio.to_thread` or see if there's an async version.
    events_iterator = await asyncio.to_thread(
        lambda: list(graph.stream(initial_state, {"recursion_limit": 5}))
    )

    for event in events_iterator:
        step_type = event.get("type", "")
        if step_type == "start":
            print("\n=== Starting New Workflow ===")
        elif step_type == "end":
            print("\n=== Workflow Complete ===")
            try:
                final_prices = safe_read_json('item_prices.json')
                recipes = safe_read_json('meals.json')
                print("\nFinal Results:")
                print(f"Total Price: ${final_prices.get('total_price', 0):.2f}")
                print(f"Budget: ${final_prices.get('budget', 0):.2f}")
                print(f"\nGenerated {len(recipes.get('recipes', []))} recipes")
            except Exception as e:
                print(f"Error reading final results: {e}")
        else:
            print("\n--- Step Details ---")
            if "messages" in event:
                print("\nMessages:")
                for msg in event["messages"][-1:]:
                    snippet = (msg.content[:200] + "...") if len(msg.content) > 200 else msg.content
                    print(f"{getattr(msg, 'name', 'Unknown')}: {snippet}")
            for key, value in event.items():
                if key != "messages":
                    print(f"{key}: {value}")
            print("-" * 50)

    return """Your Personalized Meal Plan is on the Way! 🍎🍽️

Hi there!

I’m thrilled to see you taking the first step toward healthier eating. Let’s be honest—eating healthy isn’t always easy, and eating healthy on a budget? That’s a whole new level of challenge. But don’t worry, you’re not in this alone!

I’m working hard to craft a meal plan tailored just for you, along with a custom grocery list designed to make sticking to your goals simple and stress-free. You’ll find everything you need waiting for you on the Meal Planner tab soon.

So sit tight and get ready to enjoy a delicious, healthy, and budget-friendly journey. You've got this, and I’ve got your back!

Cheers to healthy eating,
Your Meal Planner AI 🍳🌱"""


# ----------------------------------------
# Demo Usage (inside an async context)
# ----------------------------------------
if __name__ == "__main__":
    async def main():
        user_profile = UserProfile(
            age=30,
            sex="female",
            height=165,
            weight=65,
            diet_preference=["vegetarian"],
            allergies=["peanuts", "shellfish"],
            activity_level="moderate",
            goal="weight_loss",
            medical_conditions=["none"],
            budget=100.0
        )
        # response_text = await run_grocery_workflow(
        #     profile=user_profile,
        #     jwt_token="YOUR_JWT_TOKEN_HERE",
        #     user_message="Generate my groceries and meal plan!"
        # )
        # print(response_text)