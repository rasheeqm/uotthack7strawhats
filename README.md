# uotthack7strawhats
# Affordable Nutritional Meal Planning AI

A real-time multi-agent AI dietician, meal planner, and shopper at your fingertips that creates personalized, budget-friendly meal plans and grocery lists.

## Overview

This agentic AI system helps you plan nutritious meals while considering:
- Personal profile (age, height, weight)
- Dietary preferences and restrictions
- Food allergies
- Activity level
- Health goals
- Medical conditions
- Budget constraints

## Features

- **Personalized Grocery Lists**: Get customized shopping lists that fit your budget
- **Real-time Price Tracking**: Finds the most affordable options for your groceries
- **Dietary Compliance**: Ensures all recommendations align with your dietary needs
- **Flexible Planning**: Don't like a suggestion? Simply tell the system, and it will adjust

## Tech Stack

- **Frontend**: Modern, responsive UI built with React
- **Backend**: FastAPI server for efficient API handling
- **Database**: MongoDB for flexible data storage
- **AI Framework**: LangChain and LangGraph for multi-agent orchestration
- **Data Sources**:
  - grocerytracker.ca for real-time Canadian grocery prices
  - USDA FNDDS (Food and Nutrient Database for Dietary Studies) for nutrition facts and RAG-based verification

## Project Structure

Key components:
- `Agents/`: Contains the AI agents for meal planning and price tracking
  - `master_agent.py`: Main orchestrator for the system
- `web_search/`: Web scraping and price tracking modules
  - `web_search_v8.py`: Real-time grocery price tracker
- `UI/`: React-based user interface components
- `api/`: FastAPI server endpoints
- `data/`: MongoDB schemas and data management

## How It Works

1. Enter your personal profile and preferences
2. The AI generates a tailored grocery list within your budget
3. Review the suggestions and request changes if needed
4. Get real-time price comparisons for your grocery items
