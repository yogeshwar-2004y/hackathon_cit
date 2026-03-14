#!/bin/bash
# run.sh
# Start the backend and frontend concurrently

echo "Starting Backend (FastAPI on port 8000)..."
source venv/bin/activate
cd /Users/yogeshwarsakthi/Documents/CitHackathon/profitstory_ci || exit
uvicorn api.main:app --reload --port 8000 &
BACKEND_PID=$!

echo "Starting Frontend (Vite on port 3000)..."
cd frontend || exit
npm run dev -- --host &
FRONTEND_PID=$!

echo "Services started:"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop both."

# Wait for both background processes
wait $BACKEND_PID $FRONTEND_PID
