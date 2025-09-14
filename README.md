# Cold-Chain Shipment Monitoring System

**Real-Time Monitoring of Temperature-Sensitive Medical Shipments**

---

## **Project Overview**

Cold Chain Shipment Monitoring System is designed to monitor shipments of vaccines and other temperature-sensitive medical supplies. Each shipment is equipped with sensors that track **temperature, humidity, shock, location, and device health** in real-time. The system ensures the safety and quality of shipments by detecting threshold violations and generating critical alerts.

---

## **Features**

- **Real-Time Sensor Monitoring**: Tracks temperature, humidity, shock, GPS, and device health.
- **Critical Alerts**: Automatically flags threshold violations for immediate attention.
- **Database Storage**: Stores shipment and sensor data in **MySQL Workbench**.
- **Dashboard**: View shipment status, sensor readings, and alerts through a user-friendly web interface.
- **Reports**: Generate historical data reports for analysis.

---

## **System Architecture**

1. **Database Layer**
   - Tables: `shipments`, `sensors`, `sensor_readings`, `alerts`
   - Relationships visualized using **ER Diagram** in MySQL Workbench.

2. **Backend Processing**
   - Python scripts for reading sensor data and detecting threshold breaches.
   - Stores readings and alerts in the database.

3. **Frontend Dashboard**
   - Web-based interface to view shipment data.
   - Highlights critical alerts in red for easy identification.
   - Optional charts for visualizing sensor trends.

---

## **Database Schema**

**Tables:**

| Table | Description |
|-------|-------------|
| `shipments` | Stores shipment information (ID, origin, destination, dates). |
| `sensors` | Defines sensor types and measurement units. |
| `sensor_readings` | Logs sensor values with timestamps for each shipment. |
| `alerts` | Records critical threshold violations. |

**Threshold Logic:**
- Each sensor has defined min/max limits (e.g., Temperature: 2°C–8°C).  
- Readings outside these limits trigger a **critical alert**.

---

## **Sample Data**

- 5 shipments with multiple sensor readings each.
- Example reading:

| Shipment ID | Sensor | Value | Timestamp |
|-------------|--------|-------|-----------|
| 101 | Temperature | 10°C | 2025-09-14 10:00:00 |

- Example alert:

| Shipment ID | Sensor | Value | Status | Timestamp |
|-------------|--------|-------|--------|-----------|
| 101 | Temperature | 10°C | Critical | 2025-09-14 10:00:00 |

---

## **Installation & Setup**

1. **Clone the repository**
```bash
https://github.com/vineeth191004/Cold-Chain-Shipment-Monitoring.git
````

2. **Set up MySQL Database**

* Create a database in MySQL Workbench.
* Run the provided SQL schema to create tables.

3. **Install Python Dependencies**

```bash
pip install -r requirements.txt
```

4. **Run Backend Scripts**

```bash
python main.py
python app.py
```

5. **Launch Dashboard**

* Open `index.html` in a web browser to view shipment data and alerts.

---

## **Technology Stack**

| Layer         | Technology                                |
| ------------- | ----------------------------------------- |
| Database      | MySQL Workbench                           |
| Backend       | Python                                    |
| Frontend      | HTML, CSS, JavaScript                     |
| Visualization | Optional charts using Chart.js or similar |

---


Do you want me to do that version as well?
```
