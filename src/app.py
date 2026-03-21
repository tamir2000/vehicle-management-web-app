from flask import Flask, render_template, request, redirect
import pyodbc

app= Flask(__name__)

db_config = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=localhost;"
    "Database=IsraelMotors;"
    "Trusted_Connection=yes;"
)

# Split several rows result to a list
def get_dict_results(cursor):
    columns = [column[0] for column in cursor.description]
    results = []
    for row in cursor.fetchall():
        results.append(dict(zip(columns, row)))
    return results

# Route to homepage
@app.route("/")
def home_frame():
    try:
        conn = pyodbc.connect(db_config)
        cursor = conn.cursor()
        query = """
        SELECT gw.WorkerNum, gw.WorkerName, gw.WorkerSalary, count(distinct cs.SoldCarNum) AS TotalVehiclesHandled
        FROM GarageWorker gw INNER JOIN CarService cs
        ON gw.WorkerNum = cs.WorkerNum
        WHERE cs.ServiceDate BETWEEN '2025-01-01' and '2025-12-31'
        GROUP BY gw.WorkerNum, gw.WorkerName, gw.WorkerSalary
        HAVING count(distinct cs.SoldCarNum) >= 10
        """
        cursor.execute(query)
        data=get_dict_results(cursor)
        cursor.close()
        conn.close()
        
        return render_template("home.html", workers=data)
    except pyodbc.Error as err:
        return f"Database error: {err}"

# Route to "setup an appointment" page
@app.route("/appointment")
def appointment_frame(success_msg=None):
    try:
        conn = pyodbc.connect(db_config)
        cursor = conn.cursor()

        cursor.execute("SELECT WorkerNum FROM GarageWorker")
        worker_list = get_dict_results(cursor)

        cursor.execute("SELECT SoldCarNum FROM Buys")
        car_list = get_dict_results(cursor)

        cursor.close()
        conn.close()

        return render_template("appointment_form.html", workers=worker_list, cars=car_list, success_message=success_msg)

    except pyodbc.Error as err:
        return f"Database Error: {err}"

# Schedule an appointment form submission
@app.route("/submit_appointment", methods=["POST"])
def submit_appointment():
    try:
        car_num = request.form['vehicle_id']
        worker_num = request.form['employee_id']
        date = request.form['treatment_date']
        cost = request.form['treatment_cost']

        conn = pyodbc.connect(db_config)
        cursor = conn.cursor()

        check_query = f"SELECT MAX(CarTreatmentNum) FROM CarService WHERE SoldCarNum = ?"
        cursor.execute(check_query, (car_num,))
        max_car_treatment = cursor.fetchone()
        
        if max_car_treatment[0] is None:
            next_treatment_num = 1
        else:
            next_treatment_num = max_car_treatment[0] + 1

        insert_query = """
        INSERT INTO CarService (SoldCarNum, CarTreatmentNum, ServiceDate, ServiceCost, WorkerNum)
        VALUES (?, ?, ?, ?, ?)
        """
        
        cursor.execute(insert_query, (car_num, next_treatment_num, date, cost, worker_num))
        conn.commit()

        cursor.close()
        conn.close()

        success_message= (f"Car treatment Scheduled successfully! \n"
                          + f"Details: Car number: {car_num}, Treatment number: {next_treatment_num}, Date: {date}, Price: {cost}, Worker: {worker_num}"
        )

        return appointment_frame(success_msg=success_message)

    except pyodbc.Error as err:
        return f"Database Error: {err}"

# Route to the "Inspect past rentals" page
@app.route("/inspect")
def inspect_frame():
    return render_template("inspect_treatment.html")

@app.route("/inspect_result", methods=["POST"])
def inspect_result():
    try:
        client_id = request.form["client_id"]
        conn = pyodbc.connect(db_config)
        cursor = conn.cursor()
        
        # Query to get car details + rental duration
        # We join 'Rent' and 'Car' and calculate the days difference
        query = """
            SELECT 
                c.CarNum, 
                c.ManufacturerName, 
                c.CarYear, 
                c.CarColor, 
                cfr.CarDayPrice, 
                r.RentDays
            FROM Rents r
            JOIN CarForRent cfr ON r.RentedCarNum = cfr.CarNum
            JOIN Car c ON cfr.CarNum = c.CarNum
            WHERE r.CustomerNum = ?
        """
        cursor.execute(query, (client_id,))
        rentals=get_dict_results(cursor)
        
        cursor.close()
        conn.close()

        # Logic: If no rentals found, send error back to the same page
        if not rentals:
            return render_template("inspect_treatment.html", error="No rentals found for this client.")
        
        # If found, send data to the same page
        return render_template("inspect_treatment.html", rentals=rentals)

    except pyodbc.Error as err:
        return f"Database Error: {err}"

if __name__ == "__main__":
    app.run(debug=True)