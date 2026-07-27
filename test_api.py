import urllib.request
import json

# Add an employee
data = json.dumps({
    "employee_id": "EMP001",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "department": "Engineering",
    "position": "Developer",
    "base_salary": 5000,
    "hourly_rate": 25
}).encode()

req = urllib.request.Request(
    "http://localhost:8000/api/employees/",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

response = urllib.request.urlopen(req)
print(response.read().decode())