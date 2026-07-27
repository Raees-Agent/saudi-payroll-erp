# HR & Payroll ERP System

A completely free, local HR and Payroll management system built with Python, FastAPI, Streamlit, and SQLite.

## 📋 Features

- **Employee Management**: Add, view, update, and delete employee records
- **Attendance Tracking**: Log daily check-in/check-out times and working hours
- **Payroll Calculation**: Automatic salary calculation with overtime support
- **Dashboard Analytics**: Visual insights into HR metrics
- **Local & Offline**: Runs entirely on your machine with SQLite database

## 🚀 Quick Start

### 1. Install Dependencies (if needed)
```powershell
"C:\Users\Raees\AppData\Local\Programs\Python\Python312\python.exe" -m pip install -r requirements.txt
```

### 2. Start the FastAPI Server
```powershell
"C:\Users\Raees\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Open Streamlit Dashboard (in a new terminal)
```powershell
"C:\Users\Raees\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app.py --server.port 8501
```

## 📊 System URLs

| Service | URL | Description |
|---------|-----|-------------|
| API Docs | http://localhost:8000/docs | Swagger UI for API endpoints |
| FastAPI Server | http://localhost:8000 | Backend REST API |
| Streamlit Dashboard | http://localhost:8501 | Web-based user interface |

## 📁 Project Structure

```
PAYROLL/
├── requirements.txt    # Python dependencies
├── database.py         # SQLAlchemy models (employees, attendance, payroll)
├── main.py             # FastAPI application with API routes
├── payroll.py          # Payroll calculation logic
├── app.py              # Streamlit dashboard UI
└── README.md           # This file
```

## 🔧 API Endpoints

### Employees
- `GET /api/employees` - List all employees
- `GET /api/employees/{id}` - Get employee by ID
- `POST /api/employees/` - Create new employee
- `PUT /api/employees/{id}` - Update employee
- `DELETE /api/employees/{id}` - Delete employee

### Attendance
- `GET /api/attendance` - List all attendance records
- `POST /api/attendance/` - Record attendance
- `DELETE /api/attendance/{id}` - Delete attendance record

### Payroll
- `POST /api/payroll/calculate/{employee_id}` - Calculate individual payroll
- `GET /api/payroll/monthly/bulk` - Bulk calculate all payroll
- `GET /api/payroll/{employee_id}` - Get payroll history

### Dashboard
- `GET /api/dashboard/summary` - Get summary statistics

## 📝 How to Use

### Via Streamlit Dashboard (Recommended)
1. Open http://localhost:8501
2. Add employees in the "Employees" tab
3. Log attendance in the "Attendance" tab
4. View dashboard metrics on the "Dashboard" tab
5. Calculate payroll in the "Payroll" tab

### Via API (for automation)
```bash
# Add an employee
curl -X POST http://localhost:8000/api/employees/ ^
  -H "Content-Type: application/json" ^
  -d '{
    "employee_id": "EMP001",
    "first_name": "John",
    "last_name": "Doe",
    "email": "john@example.com",
    "department": "Engineering",
    "position": "Software Engineer",
    "base_salary": 5000,
    "hourly_rate": 25
  }'

# Record attendance
curl -X POST http://localhost:8000/api/attendance/ ^
  -H "Content-Type: application/json" ^
  -d '{
    "employee_id": 1,
    "date": "2024-07-06",
    "check_in": "09:00",
    "check_out": "17:30",
    "hours_worked": 8.5,
    "attendance_status": "Regular"
  }'

# Calculate payroll for employee
curl -X POST http://localhost:8000/api/payroll/calculate/1
```

## 🗄️ Database

The system uses SQLite for local storage. The database file (`payroll_db.db`) is created automatically when the application runs.

### Tables
- **employees**: Employee records with salary and department info
- **attendance**: Daily attendance logs with check-in/check-out times
- **payrolls**: Monthly payroll calculations with deductions

## ⚙️ Payroll Configuration

Payroll uses these configurable rates:
- **Regular Hours**: 8 hours per day
- **Overtime Rate**: 1.5x for hours beyond regular
- **Tax Rate**: 15% of gross salary
- **Insurance Rate**: 2% of gross salary

## 📚 Tech Stack

| Component | Technology |
|-----------|------------|
| Backend | FastAPI |
| Frontend | Streamlit |
| Database | SQLite |
| ORM | SQLAlchemy |

## 🔄 Run Both Services Simultaneously

To run both the API server and Streamlit dashboard:

**Terminal 1:**
```powershell
"C:\Users\Raees\AppData\Local\Programs\Python\Python312\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Terminal 2:**
```powershell
"C:\Users\Raees\AppData\Local\Programs\Python\Python312\python.exe" -m streamlit run app.py --server.port 8501
```

## 📦 Dependencies

- `fastapi==0.109.0`
- `uvicorn==0.27.0`
- `sqlalchemy==2.0.25`
- `pandas==2.2.0`
- `pydantic==2.5.3`
- `streamlit==1.30.0`

## 📄 License

This project is completely free and open source. Use it for personal or commercial projects.

---

**Version**: 1.0.0  
**Last Updated**: July 2026