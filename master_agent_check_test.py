from typing import Literal
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
if not os.environ.get("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = getpass.getpass("Enter your OpenAI API key: ")

llm = ChatOpenAI(model="gpt-4o", temperature=0)
# File handling functions

def extract_json_from_response(content: str) -> str:
    """Extract JSON from markdown code blocks or plain text"""
    # If content is wrapped in ```json ``` blocks
    if content.startswith('```json\n') and content.endswith('\n```'):
        return content[7:-4]  # Remove ```json\n and \n```
    # If content is wrapped in ``` ``` blocks
    elif content.startswith('```\n') and content.endswith('\n```'):
        return content[4:-4]  # Remove ```\n and \n```
    return content  # Return as is if no code blocks
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

def load_ingredients_data():
    with open('data/ingredient_to_price_and_url.json', 'r') as f:
        return json.load(f)

def save_prices(prices):
    with open('item_prices.json', 'w') as f:
        json.dump(prices, f, indent=2)

def get_next_node(last_message: BaseMessage, goto: str):
    if "FINAL ANSWER" in last_message.content:
        return END
    return goto

# Grocery List Generator Agent
grocery_list_prompt = """You are a grocery list generator. Create a list of grocery items with quantities.The quantities MUST include units (e.g., "2 lbs", "1 gallon", "500g", "3 pieces", etc).
The output must be valid JSON with this structure: 
{
    "items": [{"name": "item_name", "quantity": quantity}],
    "budget": budget_amount
}"""

grocery_list_agent = create_react_agent(
    llm,
    tools=[],  # No tools needed for initial list generation
    state_modifier=grocery_list_prompt
)

def grocery_list_node(
    state: MessagesState,
) -> Command[Literal["price_checker", END]]:
    result = grocery_list_agent.invoke(state)
    
    try:
        # Extract content from the AI message
        content = result["messages"][-1].content
        # Clean up the content by removing markdown code blocks
        cleaned_content = extract_json_from_response(content)
        
        # Parse the JSON
        grocery_list = json.loads(cleaned_content)
        
        # Debug print
        print("Parsed grocery list:", json.dumps(grocery_list, indent=2))
        
        # Save to file
        safe_write_json('agent1_output.json', grocery_list)
        
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in grocery list - {e}")
        print(f"Attempted to parse content: {content}")
        return Command(update={"messages": result["messages"]}, goto=END)
    except Exception as e:
        print(f"Error in grocery list generation: {e}")
        print(f"Content received: {content}")
        return Command(update={"messages": result["messages"]}, goto=END)
    
    goto = get_next_node(result["messages"][-1], "price_checker")
    result["messages"][-1] = HumanMessage(
        content=result["messages"][-1].content,
        name="grocery_list_generator"
    )
    
    return Command(
        update={"messages": result["messages"]},
        goto=goto
    )

# Price Checker Tool
from langchain_core.tools import tool

@tool
def find_cheapest():
    """Read the latest grocery list and find prices for items"""
    try:
        with open('agent1_output.json', 'r') as f:
            grocery_list = json.load(f)
        
        ingredients_data = load_ingredients_data()
        ingredients_dict = {item['name'].lower(): item 
                          for item in ingredients_data['ingredients']}
        
        results = []
        total_price = 0
        
        for item in grocery_list['items']:
            item_name = item['name'].lower()
            if item_name in ingredients_dict:
                item_data = ingredients_dict[item_name]
                item_total = item_data['price'] * item['quantity']
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
            'budget': grocery_list['budget']
        }
        save_prices(output_data)
        return output_data
    except Exception as e:
        return {"error": str(e)}

# Price Checker Agent
price_checker_agent = create_react_agent(
    llm,
    tools=[find_cheapest],
    state_modifier="You check prices and suggest substitutions if over budget."
)

def check_budget_condition(state: MessagesState) -> Literal["grocery_list_generator", "END"]:
    """
    Determines the next node based on budget comparison
    """
    try:
        prices_data = safe_read_json('item_prices.json')
        if not prices_data:
            print("Warning: No price data found")
            return END
            
        total_price = prices_data.get('total_price', 0)
        budget = prices_data.get('budget', 0)
        
        if total_price > budget + 5:
            items = prices_data.get('items', [])
            if not items:
                return END
                
            # Find most expensive item
            valid_items = [item for item in items if item.get('price_per_unit') is not None]
            if not valid_items:
                return END
                
            most_expensive = max(
                valid_items,
                key=lambda x: x['price_per_unit']
            )
            
            # Add suggestion context to state
            state.messages.append(
                HumanMessage(
                    content=f"The current list is over budget by ${total_price - budget:.2f}. "
                           f"Please substitute {most_expensive['name']} "
                           f"(${most_expensive['price_per_unit']}/unit) with a cheaper alternative.",
                    name="budget_checker"
                )
            )
            return "grocery_list_generator"
        return END
    except Exception as e:
        print(f"Error in budget check: {e}")
        return END

def price_checker_node(
    state: MessagesState
) -> Command[Literal["grocery_list_generator", END]]:
    result = price_checker_agent.invoke(state)
    
    try:
        prices_data = safe_read_json('item_prices.json')
        total_price = prices_data.get('total_price', 0)
        budget = prices_data.get('budget', 0)
        
        result["messages"][-1] = HumanMessage(
            content=result["messages"][-1].content,
            name="price_checker"
        )
        
        # Determine next node based on budget
        if total_price > budget + 5:
            return Command(
                update={"messages": result["messages"]},
                goto="grocery_list_generator"
            )
        else:
            return Command(
                update={"messages": result["messages"]},
                goto=END
            )
            
    except Exception as e:
        print(f"Error in price checker: {e}")
        return Command(
            update={"messages": result["messages"]},
            goto=END
        )


# Define the Graph
from langgraph.graph import StateGraph, START

workflow = StateGraph(MessagesState)

workflow.add_node("grocery_list_generator", grocery_list_node)
workflow.add_node("price_checker", price_checker_node)

# Add edges
workflow.add_edge(START, "grocery_list_generator")
workflow.add_edge("grocery_list_generator", "price_checker")
workflow.add_edge("price_checker", "grocery_list_generator")
workflow.add_edge("price_checker", END)

# Compile the graph
graph = workflow.compile()

def run_grocery_workflow(budget: float):
    # Initialize files
    initialize_files()
    
    # Create initial state with budget
    initial_state = {
        "messages": [
            HumanMessage(
                content=f"Generate a grocery list for a single person for one week based on a budget of ${budget}."
            )
        ]
    }
    
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
    run_grocery_workflow(50.0)