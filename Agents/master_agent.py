from typing import Literal, List
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.graph import MessagesState, END
from langgraph.types import Command
from pydantic import BaseModel, Field
import json
import os
import getpass
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START
import sys
from web_search_v8 import search_grocery_tracker

# Initialize OpenAI API key
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

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

# File handling functions
def extract_json_from_response(content: str) -> str:
    """Extract JSON from markdown code blocks or plain text"""
    if content.startswith('```json\n') and content.endswith('\n```'):
        return content[7:-4]
    elif content.startswith('```\n') and content.endswith('\n```'):
        return content[4:-4]
    return content

def ensure_file_exists(filename: str, default_content: dict = None):
    """Create file if it doesn't exist"""
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump(default_content or {}, f)

def safe_read_json(filename: str, default_content: dict = None):
    """Safely read JSON file with fallback to default content"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default_content or {}

def safe_write_json(filename: str, content: dict):
    """Safely write content to JSON file"""
    with open(filename, 'w') as f:
        json.dump(content, f, indent=2)

# Initialize necessary files
def initialize_files():
    ensure_file_exists('agent1_output.json', {"items": [], "budget": 0})
    ensure_file_exists('item_prices.json', {"items": [], "total_price": 0, "budget": 0})

def load_ingredients_data(item_names):
    store_type_value = "nofrills"  # Example store type value
    specific_store_value = "3643"  # Example specific store value
    out_file = "agent1_search_to_cheapest_ingredient.json"
    search_grocery_tracker(store_type_value, specific_store_value, item_names, out_file)
    with open(out_file, 'r') as f:
        return json.load(f)

def calculate_caloric_needs(profile: UserProfile) -> float:
    """Calculate estimated daily caloric needs based on user profile"""
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

# Price Checker Tool
@tool
def find_cheapest():
    """Read the latest grocery list and find prices for items"""
    try:
        print("Reading from agent1_output.json and ingredient data...")
        
        # Read the JSON file
        with open('agent1_output.json', 'r') as f:
            grocery_list = json.load(f)

        # Extract names of the items into a list
        item_names = [item['name'] for item in grocery_list['items']]

        # Print the list of names
        print(item_names)
        
        ingredients_data = load_ingredients_data(item_names)
        ingredients_dict = {item['name'].lower(): item 
                          for item in ingredients_data.get('ingredients', [])}
        
        results = []
        total_price = 0
        
        for item in grocery_list.get('items', []):
            item_name = item['name'].lower()
            
            if item_name in ingredients_dict:
                item_data = ingredients_dict[item_name]
                quantity = item['quantity']
                if isinstance(quantity, str):
                    numeric_part = ''.join(filter(str.isdigit, quantity))
                    quantity = float(numeric_part) if numeric_part else 1
                
                item_total = item_data['price']
                
                results.append({
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price_per_unit': item_data['price'],
                    'total_price': item_total,
                    'url': item_data['url']
                })
                total_price += item_total
            else:
                results.append({
                    'name': item['name'],
                    'quantity': item['quantity'],
                    'price_per_unit': None,
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
# Grocery List Node
def grocery_list_node(state: MessagesState) -> Command[Literal["price_checker"]]:
    """Process grocery list generation with user profile considerations"""
    result = grocery_list_agent.invoke(state)
    
    try:
        content = result["messages"][-1].content
        cleaned_content = extract_json_from_response(content)
        grocery_list = json.loads(cleaned_content)
        print("Parsed grocery list:", json.dumps(grocery_list, indent=2))
        safe_write_json('agent1_output.json', grocery_list)
        
    except Exception as e:
        print(f"Error in grocery list generation: {e}")
        return Command(update={"messages": result["messages"]}, goto="price_checker")
    
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="grocery_list_generator"
    )
    
    return Command(
        update={"messages": result["messages"]},
        goto="price_checker"
    )

# Price Checker Agent
price_checker_agent = create_react_agent(
    llm,
    tools=[find_cheapest],
    state_modifier="You check prices and suggest substitutions if over budget."
)

def price_checker_node(state: MessagesState) -> MessagesState:
    result = price_checker_agent.invoke(state)
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="price_checker"
    )
    return result

def route_by_budget(state: MessagesState) -> Literal["grocery_list_generator", "end"]:
    """Route based on budget comparison. Simply ends if under budget, suggests replacements if over."""
    try:
        prices_data = safe_read_json('item_prices.json')
        
        # Clean and convert price values
        def clean_price(price_str):
            if isinstance(price_str, (int, float)):
                return float(price_str)
            if isinstance(price_str, str):
                cleaned = ''.join(char for char in price_str if char.isdigit() or char == '.')
                return float(cleaned) if cleaned else 0.0
            return 0.0
        
        # Ensure values are float type
        total_price = clean_price(prices_data.get('total_price', 0))
        budget = clean_price(prices_data.get('budget', 0))
        budget_threshold = budget * 1.10
        
        # If under budget (+10% buffer), just end
        if total_price <= budget_threshold:
            return "end"
        
        # Over budget - find most expensive item and suggest replacement
        items = prices_data.get('items', [])
        valid_items = []
        for item in items:
            try:
                price_per_unit = clean_price(item.get('price_per_unit'))
                if price_per_unit > 0:
                    item['price_per_unit'] = price_per_unit
                    valid_items.append(item)
            except (TypeError, ValueError):
                continue
                
        if valid_items:
            most_expensive = max(valid_items, key=lambda x: x['price_per_unit'])
            if 'messages' not in state:
                state['messages'] = []
            state['messages'].append(
                HumanMessage(
                    content=f"The total price ${total_price:.2f} is over budget threshold "
                           f"(${budget_threshold:.2f}). Please replace {most_expensive['name']} "
                           f"(${most_expensive['price_per_unit']:.2f}/unit) with a cheaper alternative.",
                    name="budget_router"
                )
            )
        return "grocery_list_generator"
            
    except Exception as e:
        print(f"Error in route_by_budget: {e}")
        return "end"

def run_grocery_workflow(profile: UserProfile):
    """Run the grocery list workflow with user profile"""
    initialize_files()
    
    # Create grocery list agent with profile-based prompt
    global grocery_list_agent
    grocery_list_agent = create_react_agent(
        llm,
        tools=[],
        state_modifier=create_grocery_prompt(profile)
    )
    
    initial_state = {
        "messages": [
            HumanMessage(
                content=f"Generate a personalized grocery list based on the provided profile and requirements."
            )
        ]
    }
    
    # Initialize the graph
    workflow = StateGraph(MessagesState)

    # Add nodes
    workflow.add_node("grocery_list_generator", grocery_list_node)
    workflow.add_node("price_checker", price_checker_node)

    # Add edges with conditional routing
    workflow.add_edge(START, "grocery_list_generator")
    workflow.add_edge("grocery_list_generator", "price_checker")
    workflow.add_conditional_edges(
        "price_checker",
        route_by_budget,
        {
            "grocery_list_generator": "grocery_list_generator",
            "end": END
        }
    )

    # Compile the graph
    graph = workflow.compile()
    
    events = graph.stream(
        initial_state,
        {"recursion_limit": 5},
    )
    
    for event in events:
        step_type = event.get("type", "")
        if step_type == "start":
            print("\n=== Starting New Workflow ===")
        elif step_type == "end":
            print("\n=== Workflow Complete ===")
            try:
                final_prices = safe_read_json('item_prices.json')
                print("\nFinal Results:")
                print(f"Total Price: ${final_prices.get('total_price', 0):.2f}")
                print(f"Budget: ${final_prices.get('budget', 0):.2f}")
            except Exception as e:
                print(f"Error reading final results: {e}")
        else:
            print("\n--- Step Details ---")
            if "messages" in event:
                print("\nMessages:")
                for msg in event["messages"][-1:]:
                    print(f"{msg.name if hasattr(msg, 'name') else 'Unknown'}: {msg.content[:200]}...")
            for key, value in event.items():
                if key != "messages":
                    print(f"{key}: {value}")
        print("-" * 50)


def run_grocery_workflow(profile: UserProfile):
    """Run the grocery list workflow with user profile"""
    initialize_files()
    
    # Create grocery list agent with profile-based prompt
    global grocery_list_agent
    grocery_list_agent = create_react_agent(
        llm,
        tools=[],
        state_modifier=create_grocery_prompt(profile)
    )
    
    initial_state = {
        "messages": [
            HumanMessage(
                content=f"Generate a personalized grocery list based on the provided profile and requirements."
            )
        ]
    }
    
    # Initialize the graph
    workflow = StateGraph(MessagesState)

    # Add nodes
    workflow.add_node("grocery_list_generator", grocery_list_node)
    workflow.add_node("price_checker", price_checker_node)

    # Add edges with conditional routing
    workflow.add_edge(START, "grocery_list_generator")
    workflow.add_edge("grocery_list_generator", "price_checker")
    workflow.add_conditional_edges(
        "price_checker",
        route_by_budget,
        {
            "grocery_list_generator": "grocery_list_generator",
            "end": END
        }
    )

    # Compile the graph
    graph = workflow.compile()
    
    events = graph.stream(
        initial_state,
        {"recursion_limit": 150},
    )
    
    for event in events:
        step_type = event.get("type", "")
        if step_type == "start":
            print("\n=== Starting New Workflow ===")
        elif step_type == "end":
            print("\n=== Workflow Complete ===")
            try:
                final_prices = safe_read_json('item_prices.json')
                print("\nFinal Results:")
                print(f"Total Price: ${final_prices.get('total_price', 0):.2f}")
                print(f"Budget: ${final_prices.get('budget', 0):.2f}")
            except Exception as e:
                print(f"Error reading final results: {e}")
        else:
            print("\n--- Step Details ---")
            if "messages" in event:
                print("\nMessages:")
                for msg in event["messages"][-1:]:
                    print(f"{msg.name if hasattr(msg, 'name') else 'Unknown'}: {msg.content[:200]}...")
            for key, value in event.items():
                if key != "messages":
                    print(f"{key}: {value}")
        print("-" * 50)

if __name__ == "__main__":
    # Example usage
    user_profile = UserProfile(
        age=30,
        sex="female",
        height=165,  # cm
        weight=65,   # kg
        diet_preference=["vegetarian"],
        allergies=["peanuts", "shellfish"],
        activity_level="moderate",
        goal="weight_loss",
        medical_conditions=["none"],
        budget=20.0
    )
    
    run_grocery_workflow(user_profile)