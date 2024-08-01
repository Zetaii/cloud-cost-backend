from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
from pydantic import BaseModel
from datetime import datetime
import json

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cloud-cost-frontend.vercel.app",
        "http://localhost:3000"  # Add this for local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class CloudCost(BaseModel):
    month: str
    cost: float

class ServiceUsage(BaseModel):
    labels: List[str]
    data: List[float]

class Resource(BaseModel):
    name: str
    type: str
    cost: float

class CostEstimationParams(BaseModel):
    instanceCount: int
    hoursPerDay: int
    daysPerMonth: int
    costPerHour: float

# Sample data
cloud_costs = [
    {"month": "January", "cost": 65},
    {"month": "February", "cost": 59},
    {"month": "March", "cost": 80},
    {"month": "April", "cost": 81},
    {"month": "May", "cost": 56},
    {"month": "June", "cost": 55},
    {"month": "July", "cost": 40},
]

service_usage = {
    'labels': ['Compute', 'Storage', 'Networking', 'Database', 'Analytics'],
    'data': [100, 150, 100, 200, 250],
}

daily_costs = {
    'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
    'data': [120, 190, 30, 50, 20, 30, 150],
}

resources = [
    {"name": 'Web Server', "type": 'EC2', "cost": 100},
    {"name": 'Database', "type": 'RDS', "cost": 200},
    {"name": 'Storage', "type": 'S3', "cost": 50},
]

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)

manager = ConnectionManager()

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# API endpoints
@app.get("/cloud-costs")
async def get_cloud_costs():
    return cloud_costs

@app.get("/service-usage")
async def get_service_usage():
    return service_usage

@app.get("/daily-costs")
async def get_daily_costs():
    return daily_costs

@app.get("/resources")
async def get_resources():
    return resources

@app.post("/estimate-cost")
async def estimate_cost(params: CostEstimationParams):
    monthly_cost = params.instanceCount * params.hoursPerDay * params.daysPerMonth * params.costPerHour
    return {"estimatedMonthlyCost": monthly_cost}

@app.get("/filtered-costs")
async def get_filtered_costs(start_date: str, end_date: str):
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    filtered_costs = [cost for cost in cloud_costs if start <= datetime.strptime(cost['month'], "%B") <= end]
    return filtered_costs

@app.put("/update-cloud-costs")
async def update_cloud_costs(updated_costs: List[CloudCost]):
    global cloud_costs
    cloud_costs = [cost.dict() for cost in updated_costs]
    await manager.broadcast({"type": "cloud_costs", "data": cloud_costs})
    return {"message": "Cloud costs updated successfully"}

@app.put("/update-service-usage")
async def update_service_usage(updated_usage: ServiceUsage):
    global service_usage
    service_usage = updated_usage.dict()
    await manager.broadcast({"type": "service_usage", "data": service_usage})
    return {"message": "Service usage updated successfully"}

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)