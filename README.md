# Database Chat AI 🤖

A full-stack LLM-integrated web application that lets users design 
database schemas through natural language — no SQL knowledge required.

🔗 **Live Demo:** https://database-chat-ai-frontend.up.railway.app/

## What it does
Type what you need in plain English. The app uses OpenAI GPT to 
generate structured schemas instantly, reducing design time from 
30 minutes to under 10 seconds per query.

## Tech Stack
`FastAPI` `React` `OpenAI API` `MongoDB` `PostgreSQL` `Docker`

## Features
- Natural language → database schema generation (relational & non-relational)
- 8 REST API endpoints for auth and AI-driven schema generation
- Interactive schema editor in the frontend
- Dual-database architecture (MongoDB + PostgreSQL) adapting to user needs
- Fully containerized 4-service app via Docker

## Architecture
React frontend → FastAPI backend → OpenAI GPT (prompt engineering) 
→ dynamic schema output → MongoDB or PostgreSQL based on schema type

## Run Locally
git clone https://github.com/NAKSHATHRA305/Database_Chat_AI
docker-compose up --build

