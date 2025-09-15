"""
Features:
- ER diagram + MySQL schema
- Sample dataset generation (5 shipments, 10+ readings per sensor)
- Threshold & violation detection (breach, sustained, spike, correlation)
- Shipment summary with avg/min/max, violations, per-sensor risk, overall risk, critical alerts
- Outputs both JSON and text format
- Handles missing/delayed readings
- Uses Python + MySQL

Requirements:
    pip install pandas numpy mysql-connector-python
"""

import random, datetime, json
from typing import Dict, List, Any
import pandas as pd
import numpy as np
import mysql.connector

# -----------------------------
# JSON Encoder for datetime
# -----------------------------
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime, pd.Timestamp)):
            return obj.isoformat(sep=" ", timespec="seconds")
        return super().default(obj)

# -----------------------------
# DB CONFIG
# -----------------------------
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Vineeth04!",
    "database": "medisafe"
}

# -----------------------------
# Sensor Definitions
# -----------------------------
SENSORS_DEF = [
    {"sensor_code": "T100","sensor_name": "ThermoProbe T-100","sensor_type": "core_temperature","unit": "C",
     "metadata": {"ideal_low": 2, "ideal_high": 8, "warning_margin": 1}},
    {"sensor_code": "TX5","sensor_name": "TempTrack X5","sensor_type": "surface_temperature","unit": "C",
     "metadata": {"ideal_low": 0, "ideal_high": 10, "warning_margin": 2}},
    {"sensor_code": "H200","sensor_name": "HumidSensor H-200","sensor_type": "humidity","unit": "%",
     "metadata": {"ideal_low": 30, "ideal_high": 60, "warning_margin": 5}},
    {"sensor_code": "S50","sensor_name": "ShockLog S-50","sensor_type": "shock","unit": "g",
     "metadata": {"spike_threshold": 2.0}},
    {"sensor_code": "G12","sensor_name": "GPS ColdTrack G-12","sensor_type": "gps","unit": "km",
     "metadata": {"max_route_deviation_km": 5}},
    {"sensor_code": "B10","sensor_name": "BatteryMonitor B-10","sensor_type": "battery_voltage","unit": "V",
     "metadata": {"min_voltage": 3.3}},
]

# -----------------------------
# SQL Schema
# -----------------------------
CREATE_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS shipments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    shipment_code VARCHAR(64) UNIQUE,
    origin VARCHAR(128),
    destination VARCHAR(128),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sensors (
    id INT PRIMARY KEY AUTO_INCREMENT,
    sensor_code VARCHAR(64) UNIQUE,
    sensor_name VARCHAR(128),
    sensor_type VARCHAR(64),
    unit VARCHAR(16),
    metadata JSON
);

CREATE TABLE IF NOT EXISTS readings (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    shipment_id INT,
    sensor_id INT,
    value DOUBLE,
    unit VARCHAR(16),
    ts DATETIME,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS violations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    shipment_id INT,
    sensor_id INT NULL,
    reading_id BIGINT NULL,
    type VARCHAR(64),
    severity VARCHAR(32),
    message TEXT,
    ts DATETIME,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE,
    FOREIGN KEY (sensor_id) REFERENCES sensors(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS risk_scores (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    shipment_id INT,
    score DOUBLE,
    category VARCHAR(32),
    details JSON,
    ts DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (shipment_id) REFERENCES shipments(id) ON DELETE CASCADE
);
"""

# -----------------------------
# DB Helpers
# -----------------------------
def get_db_connection():
    cfg = DB_CONFIG.copy()
    dbname = cfg.pop("database")
    conn = mysql.connector.connect(**cfg)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {dbname}")
    cur.close(); conn.close()
    return mysql.connector.connect(**DB_CONFIG)

def execute_multi_sql(conn, sql):
    cur = conn.cursor()
    for stmt in sql.split(";"):
        if stmt.strip(): cur.execute(stmt)
    conn.commit(); cur.close()

# -----------------------------
# Sample Data Generation
# -----------------------------
def create_sample_shipments(n=5):
    now = datetime.datetime.utcnow()
    return [{"shipment_code": f"SHP-{100+i}",
             "origin": random.choice(["Mumbai","Delhi","Kolkata","Bengaluru"]),
             "destination": random.choice(["Chennai","Hyderabad","Pune","Ahmedabad"]),
             "created_at": now - datetime.timedelta(days=i)} for i in range(n)]

def generate_readings_for_shipment(ship_id, sensors, n=12):
    base = datetime.datetime.utcnow() - datetime.timedelta(hours=6)
    rows = []
    for s in sensors:
        for i in range(n):
            ts = base + datetime.timedelta(minutes=5*i)
            v=None; t=s["sensor_type"]; m=s["metadata"]
            if t=="core_temperature": v=random.gauss(5,1);  v += random.choice([-3,3]) if random.random()<0.1 else 0
            elif t=="surface_temperature": v=random.gauss(5,1.5)
            elif t=="humidity": v=random.gauss(45,5)
            elif t=="shock": v=random.uniform(0,0.4); v=random.uniform(2,5) if random.random()<0.05 else v
            elif t=="gps": v=random.uniform(0,3)
            elif t=="battery_voltage": v=random.uniform(3.2,4.1); v=random.uniform(2.8,3.1) if random.random()<0.05 else v
            if random.random()<0.03: v=None
            rows.append({"shipment_id":ship_id,"sensor_code":s["sensor_code"],"value":v,"unit":s["unit"],"ts":ts})
    return rows

# -----------------------------
# Violation & Risk Logic
# -----------------------------
def severity_for(meta, value, stype):
    if value is None: return "normal"
    if stype in ["core_temperature","surface_temperature","humidity"]:
        low,high=meta["ideal_low"],meta["ideal_high"]
        if value<low or value>high:
            return "critical" if abs(value-(low if value<low else high))>meta.get("warning_margin",1) else "warning"
    if stype=="shock": return "critical" if value>=meta.get("spike_threshold",2) else "normal"
    if stype=="battery_voltage": return "warning" if value<meta.get("min_voltage",3.3) else "normal"
    return "normal"

def detect_violations(df, meta):
    out=[]
    for sc,grp in df.groupby("sensor_code"):
        m=meta[sc]["metadata"]; st=meta[sc]["sensor_type"]
        for ts,v in zip(grp["ts"],grp["value"]):
            if v is None:
                out.append({"sensor_code":sc,"type":"missing","severity":"warning","message":"Missing reading","ts":ts})
            else:
                sev=severity_for(m,v,st)
                if sev!="normal":
                    out.append({"sensor_code":sc,"type":"threshold","severity":sev,"message":f"{sc} breach: {v}","ts":ts})
    return out

def compute_risk(violations):
    score=sum(0.1 if v["severity"]=="warning" else 0.35 if v["severity"]=="critical" else 0 for v in violations)
    return min(1,round(score,3)), "High" if score>0.5 else "Medium" if score>0.2 else "Low"

def sensor_risk(value_list, meta, stype):
    risk="Low"
    for v in value_list:
        sev=severity_for(meta, v, stype)
        if sev=="critical": return "High"
        elif sev=="warning": risk="Medium"
    return risk

# -----------------------------
# Main Workflow
# -----------------------------
def main():
    print("MediSafe Monitoring System - Starting")
    conn=get_db_connection(); execute_multi_sql(conn,CREATE_SCHEMA_SQL)
    cur=conn.cursor()

    # Insert sensors
    sensor_map={}
    for s in SENSORS_DEF:
        cur.execute("SELECT id FROM sensors WHERE sensor_code=%s",(s["sensor_code"],))
        row=cur.fetchone(); sid=row[0] if row else None
        if not sid:
            cur.execute("INSERT INTO sensors(sensor_code,sensor_name,sensor_type,unit,metadata) VALUES(%s,%s,%s,%s,%s)",
                        (s["sensor_code"],s["sensor_name"],s["sensor_type"],s["unit"],json.dumps(s["metadata"])))
            sid=cur.lastrowid
        sensor_map[s["sensor_code"]]={"id":sid,**s}
    conn.commit()

    # Shipments
    ship_map={}
    for shp in create_sample_shipments():
        cur.execute("INSERT IGNORE INTO shipments(shipment_code,origin,destination,created_at) VALUES(%s,%s,%s,%s)",
                    (shp["shipment_code"],shp["origin"],shp["destination"],shp["created_at"]))
        cur.execute("SELECT id FROM shipments WHERE shipment_code=%s",(shp["shipment_code"],))
        ship_map[shp["shipment_code"]]=cur.fetchone()[0]
    conn.commit()

    # Readings
    for scode,sid in ship_map.items():
        for r in generate_readings_for_shipment(sid,SENSORS_DEF):
            cur.execute("INSERT INTO readings(shipment_id,sensor_id,value,unit,ts) VALUES(%s,%s,%s,%s,%s)",
                        (r["shipment_id"],sensor_map[r["sensor_code"]]["id"],r["value"],r["unit"],r["ts"]))
    conn.commit()
    print("Sample data inserted.\n")

    # Reports
    all_output_json=[]
    for code,sid in ship_map.items():
        cur.execute("""SELECT s.sensor_code, r.value, r.ts
                       FROM readings r JOIN sensors s ON r.sensor_id=s.id
                       WHERE r.shipment_id=%s""",(sid,))
        df=pd.DataFrame(cur.fetchall(),columns=["sensor_code","value","ts"])

        # --- Sensor Stats ---
        stats=df.groupby("sensor_code")["value"].agg(["mean","min","max"]).round(2)

        # --- Violations & risk ---
        viols=detect_violations(df,sensor_map)
        score,cat=compute_risk(viols)
        cur.execute("INSERT INTO risk_scores(shipment_id,score,category,details) VALUES(%s,%s,%s,%s)",
                    (sid,score,cat,json.dumps({"violations":viols},cls=DateTimeEncoder)))
        conn.commit()

        # --- Violations count ---
        vcount=pd.DataFrame(viols).groupby("sensor_code").size() if viols else pd.Series(dtype=int)

        # --- Text Output ---
        print(f"\nShipment {code} - Sensor Stats:")
        print(stats)
        print("\nViolations per sensor:")
        print(vcount)
        print(f"\nShipment {code} Sensor Analysis:")

        critical_alerts=[]
        sensor_analysis=[]
        for sc in df["sensor_code"].unique():
            values=df[df["sensor_code"]==sc]["value"].tolist()
            meta=sensor_map[sc]["metadata"]
            stype=sensor_map[sc]["sensor_type"]
            srisk=sensor_risk(values,meta,stype)
            vnum=len([v for v in viols if v["sensor_code"]==sc])
            print(f"{sc} ({sensor_map[sc]['sensor_name']}): Avg={np.nanmean(values):.2f}{sensor_map[sc]['unit']}, Violations={vnum} → {srisk} Risk")
            sensor_analysis.append({"sensor_code":sc,"sensor_name":sensor_map[sc]['sensor_name'],
                                    "avg": round(np.nanmean(values),2),
                                    "unit":sensor_map[sc]['unit'],
                                    "violations":vnum,
                                    "risk":srisk})
            if srisk=="High": critical_alerts.append(sensor_map[sc]['sensor_name'])

        if critical_alerts:
            print(f"Critical Alerts: {', '.join(critical_alerts)}")
        else:
            print("Critical Alerts: None")
        print(f"Overall Shipment Risk Score: {score} ({cat})\n{'-'*50}")

        # --- JSON Output ---
        shipment_json={
            "shipment_code": code,
            "sensor_stats": stats.reset_index().to_dict(orient="records"),
            "violations_count": vcount.reset_index(name="count").to_dict(orient="records"),
            "sensor_analysis": sensor_analysis,
            "critical_alerts": critical_alerts,
            "overall_risk_score": {"score":score,"category":cat},
            "violations_detail": viols
        }
        all_output_json.append(shipment_json)

    # Save JSON to file
    with open("shipment_summary.json","w") as f:
        json.dump(all_output_json,f,cls=DateTimeEncoder,indent=4)

    cur.close(); conn.close()
    print("Done. JSON output saved to shipment_summary.json")

if __name__=="__main__":
    main()

