import urllib.request
import json

# Record attendance for employee 1
data = json.dumps({
    "employee_id": 1,
    "date": "2026-07-06",
    "check_in": "09:00",
    "check_out": "18:00",
    "hours_worked": 9.0,
    "attendance_status": "Regular"
}).encode()

req = urllib.request.Request(
    "http://localhost:8000/api/attendance/",
    data=data,
    headers={"Content-Type": "application/json"},
    method="POST"
)

response = urllib.request.urlopen(req)
print(response.read().decode())