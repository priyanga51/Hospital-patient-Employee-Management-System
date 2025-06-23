import streamlit as st
import pyodbc
import datetime
import smtplib
import os
import pandas as pd
import time
import json
import speech_recognition as sr
import pyaudio
import wave
import pyodbc
import datetime
import google.generativeai as genai
from fpdf import FPDF  # PDF Library
import google.generativeai as genai
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# Set up Google Gemini API
GEMINI_API_KEY =  "YOUR_YOUTUBE_API_KEY" # Replace with your actual API key
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-pro")

# Database Connection
SERVER = "DESKTOP-F4API67\\SQLEXPRESS"  # Change this to your SQL Server name
DATABASE = "HospitalDB"

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_SENDER = "Enter Your Email"  # Replace with your email
EMAIL_PASSWORD = "Enter Your  Password " # Use App Password for security


appointments = {}  # Dictionary to store patient appointments
def get_db_connection():
    try:
        conn = pyodbc.connect(f'DRIVER={{SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;')
        return conn
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

# ✅ Function to Get the Next Available Patient ID
def get_next_patient_id():
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ISNULL(MAX(HospitalID), 0) + 1 FROM Patients")  # Auto-increment next ID
        next_id = cursor.fetchone()[0]
        conn.close()
        return next_id
    return 1  # If no records exist, start from 1

    # ✅ Function to Add Patient


# ✅ Function to Add a New Patient
def add_patient(name, age, phone, address, height, weight, blood_pressure, diseases, first_visit, billing_details,
                oxygen_level):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        first_visit_str = first_visit.strftime('%Y-%m-%d')

        # ✅ Check if phone number already exists
        cursor.execute("SELECT COUNT(*) FROM Patients WHERE Phone = ?", (phone,))
        if cursor.fetchone()[0] > 0:
            st.error("❌ Patient with this phone number already exists!")
            conn.close()
            return

        query = """INSERT INTO Patients (Name, Age, Phone, Address, Height, Weight, BloodPressure, Diseases, FirstVisitDate, BillingDetails, OxygenLevel) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
        cursor.execute(query, (
        name, age, phone, address, height, weight, blood_pressure, diseases, first_visit_str, billing_details,
        oxygen_level))

        conn.commit()
        conn.close()
        st.success(f"✅ Patient Added Successfully!")

        # ✅ Function to Add Visit for Returning Patients
def add_patient_visit(hospital_id, visit_date, symptoms, temperature, oxygen_level, blood_pressure):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        visit_date_str = visit_date.strftime('%Y-%m-%d')

        query = """INSERT INTO PatientVisits (HospitalID, VisitDate, Symptoms, Temperature, OxygenLevel, BloodPressure, OxygenLevel) 
                   VALUES (?, ?, ?, ?, ?, ?)"""
        cursor.execute(query, (hospital_id, visit_date_str, symptoms, temperature, oxygen_level, blood_pressure, oxygen_level))
        conn.commit()
        conn.close()
        st.success("✅ Visit Record Added Successfully!")

# ✅ Function to Retrieve Patient Records
def get_patient_record(hospital_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = "SELECT * FROM Patients WHERE HospitalID = ?"
        cursor.execute(query, (hospital_id,))
        record = cursor.fetchone()
        conn.close()
        return record
    return None

# ✅ Function to Retrieve Visit History
#def get_visit_history(hospital_id):
 #   conn = get_db_connection()
  #  if conn:
  #      cursor = conn.cursor()
  #      query = "SELECT VisitDate, Symptoms, Temperature, OxygenLevel, BloodPressure FROM PatientVisits WHERE HospitalID = ? ORDER BY VisitDate DESC"
  #      cursor.execute(query, (hospital_id,))
   #     visits = cursor.fetchall()
   #     conn.close()
   #     return visits
  #  return None


def add_patient_visit(hospital_id, visit_date, symptoms, temperature, oxygen_level, blood_pressure):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        visit_date_str = visit_date.strftime('%Y-%m-%d')

        query = """INSERT INTO PatientVisits (HospitalID, VisitDate, Symptoms, Temperature, OxygenLevel, BloodPressure) 
                   VALUES (?, ?, ?, ?, ?, ?)"""  # ✅ Fixed query

        cursor.execute(query, (hospital_id, visit_date_str, symptoms, temperature, oxygen_level, blood_pressure))  # ✅ 6 values
        conn.commit()
        conn.close()
        st.success("✅ Visit Record Added Successfully!")

# -------------------- EMAIL FUNCTION --------------------

def send_email(receiver_email, patient_id, appointment_date, subject, body):
    """Send an email notification (confirmation or reminder)."""
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = receiver_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())
        server.quit()
        return "📩 Email Sent Successfully!"
    except Exception as e:
        return f"❌ Failed to send email: {str(e)}"


# -------------------- APPOINTMENT BOOKING --------------------

def book_appointment(patient_id, date, email):
    """Book an appointment and send confirmation email."""
    if patient_id in appointments:
        return f"⚠️ Patient {patient_id} already has an appointment on {appointments[patient_id]['date']}."

    appointments[patient_id] = {"date": date, "email": email}

    # Print stored data for debugging
    print("Appointments Dictionary:", appointments)

    # Send Confirmation Email
    subject = "Appointment Confirmation - Hospital"
    body = f"""
    Dear Patient {patient_id},

    Your appointment has been successfully booked for {date}.

    Thank you for choosing our hospital.

    Best Regards,
    Hospital Management
    """
    email_status = send_email(email, patient_id, date, subject, body)

    return f"✅ Appointment confirmed for Patient {patient_id} on {date}.\n{email_status}"


# -------------------- SEND REMINDER EMAILS --------------------

def send_reminders():
    """Send reminders to all patients who have an appointment tomorrow."""
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")

    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT patient_id, email, appointment_date FROM Appointments WHERE appointment_date = ?", (tomorrow,))
        reminders = cursor.fetchall()
        conn.close()

        if reminders:
            for patient_id, email, appointment_date in reminders:
                subject = "Appointment Reminder - Hospital"
                body = f"""
                Dear Patient {patient_id},

                This is a reminder that you have an appointment scheduled for {appointment_date}.
                Please ensure you arrive on time.

                Best Regards,
                Hospital Management
                """
                email_status = send_email(email, patient_id, appointment_date, subject, body)
                st.success(f"📩 Reminder sent to {email} ✅")
                print(f"Reminder sent to {email} - Status: {email_status}")
        else:
            st.info("✅ No reminders for tomorrow.")
            print("No reminders found for tomorrow.")


#  Auto-Generate Employee ID

def generate_employee_id():
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(EmployeeID) FROM Employees")
        max_id = cursor.fetchone()[0]

        conn.close()

        if max_id is None:
            return 1001  # Start from 1001 if no employees exist
        else:
            return max_id + 1

    except Exception as e:
        st.error(f"Error Generating Employee ID: {e}")
        return None



#  Function to Add Employee

def add_employee(full_name, department, role, contact, email, salary, join_date, shift, status):
    conn = get_db_connection()
    if conn is None:
        return

    try:
        cursor = conn.cursor()

        # Convert date to string format (YYYY-MM-DD)
        join_date_str = join_date.strftime("%Y-%m-%d")

        # Ensure salary is a float
        salary = float(salary)

        # Insert employee (Fix: Added 'Status' column to match values)
        cursor.execute("""
            INSERT INTO Employees (FullName, Department, Role, Contact, Email, Salary, JoinDate, Shift, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (full_name, department, role, contact, email, salary, join_date_str, shift, status))

        conn.commit()
        conn.close()
        st.success(f"✅ Employee '{full_name}' added successfully!")

    except Exception as e:
        st.error(f"❌ Error Adding Employee: {e}")



#  Function to Fetch Employee Details

def get_employee_details(employee_id):
    conn = get_db_connection()
    if conn is None:
        return None

    try:
        query = f"SELECT * FROM Employees WHERE EmployeeID = ?"
        df = pd.read_sql(query, conn, params=[employee_id])
        conn.close()

        if df.empty:
            return None
        return df.iloc[0]  # Return first matching record

    except Exception as e:
        st.error(f"❌ Error Fetching Employee Data: {e}")
        return None



#  Function to Generate PDF

def generate_employee_pdf(employee_data):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Arial", style='B', size=16)
    pdf.cell(200, 10, "Employee Details Report", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, f"Employee ID: {employee_data['EmployeeID']}", ln=True)
    pdf.cell(200, 10, f"Full Name: {employee_data['FullName']}", ln=True)
    pdf.cell(200, 10, f"Department: {employee_data['Department']}", ln=True)
    pdf.cell(200, 10, f"Role: {employee_data['Role']}", ln=True)
    pdf.cell(200, 10, f"Contact: {employee_data['Contact']}", ln=True)
    pdf.cell(200, 10, f"Email: {employee_data['Email']}", ln=True)
    pdf.cell(200, 10, f"Salary: ${employee_data['Salary']}", ln=True)
    pdf.cell(200, 10, f"Joining Date: {employee_data['JoinDate']}", ln=True)
    pdf.cell(200, 10, f"Shift: {employee_data['Shift']}", ln=True)
    pdf.cell(200, 10, f"Status: {employee_data['Status']}", ln=True)

    pdf_output_path = "employee_details.pdf"
    pdf.output(pdf_output_path)

    return pdf_output_path



# --------------------------- Speech-to-Text Processing ---------------------------
def transcribe_audio(file_path):
    """Converts speech to text & ensures the final output is in English."""
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)

    try:
        transcript = recognizer.recognize_google(audio, language='ta-IN')
        st.success("✅ Transcription Successful!")

        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(f"Translate the following to English:\n\n{transcript}")
        transcript = response.text.strip() if response and hasattr(response, "text") else transcript

    except sr.UnknownValueError:
        transcript = "⚠ Could not understand the audio."
    except sr.RequestError:
        transcript = "⚠ API unavailable."

    extracted_tests = extract_medical_tests(transcript)
    return transcript, extracted_tests


def extract_medical_tests(text):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        response = model.generate_content(f"Extract medical tests from this conversation: {text}")

        # Fix formatting: Remove *, new lines, and empty entries
        tests = response.text.split("\n") if response and hasattr(response, "text") else []
        cleaned_tests = [test.replace("*", "").strip() for test in tests if test.strip()]

        return cleaned_tests
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        return []

def fetch_patient_record(record_id):
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        st.write(f"🔎 Searching for Record ID: {record_id}")  # Debugging

        query = "SELECT * FROM dbo.PatientRecords WHERE ID = ?"
        cursor.execute(query, (record_id,))
        result = cursor.fetchone()

        if result:
            st.write("✅ Record Found:", result)  # Debugging
        else:
            st.error("⚠ No record found in the database.")  # This might be the error cause

        conn.close()
        return result



# ----------------------------- Patient Records Management -----------------------------
def save_patient_record(patient_id, doctor_id, recording_path, transcript, extracted_tests):
    if not extracted_tests:
        st.warning("No tests were extracted. Please check the transcription.")
    conn = get_db_connection()

    if conn:
        cursor = conn.cursor()

        # ✅ Ensure correct format of test status
        test_status_dict = {test.strip(): "Pending" for test in extracted_tests}

        query = """
        INSERT INTO dbo.PatientRecords (PatientID, DoctorID, RecordTimestamp, RecordingPath, Transcript, ExtractedTests, TestStatus)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        cursor.execute(query, (
            patient_id, doctor_id, datetime.datetime.now(), recording_path, transcript,
            json.dumps(extracted_tests), json.dumps(test_status_dict)
        ))
        conn.commit()
        conn.close()
        st.success("✅ Transcription and extracted tests saved successfully!")


def get_patient_records(patient_id):
    """Retrieves all records for a given Patient ID"""
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        query = "SELECT * FROM dbo.PatientRecords WHERE PatientID = ? ORDER BY RecordTimestamp ASC"
        cursor.execute(query, (patient_id,))
        records = cursor.fetchall()
        conn.close()
        return records
    return None


# ----------------------------- Update Test Status -----------------------------
def update_test_status(record_id, test_name, new_status):
    conn = get_db_connection()

    if conn:
        cursor = conn.cursor()

        # 🔍 Fetch current TestStatus from database
        cursor.execute("SELECT TestStatus FROM dbo.PatientRecords WHERE ID = ?", (record_id,))
        row = cursor.fetchone()

        if row and row[0]:  # Ensure there is data
            try:
                # ✅ Fix JSON Parsing
                test_status_dict = json.loads(row[0])

                # ✅ Normalize test names for case-insensitive matching
                normalized_test_name = test_name.strip().lower()

                # ✅ Find the matching test name in the dictionary
                matching_test_name = next(
                    (key for key in test_status_dict.keys() if key.strip().lower() == normalized_test_name),
                    None
                )

                if matching_test_name:
                    # ✅ Update status
                    test_status_dict[matching_test_name] = new_status
                else:
                    st.error(
                        f"⚠ Test '{test_name}' not found in record ID {record_id}. Available tests: {list(test_status_dict.keys())}"
                    )
                    return

                # ✅ Convert back to JSON
                updated_test_status_json = json.dumps(test_status_dict)

                # ✅ Update database
                cursor.execute("UPDATE dbo.PatientRecords SET TestStatus = ? WHERE ID = ?",
                               (updated_test_status_json, record_id))
                conn.commit()

                st.success(f"✅ Test '{matching_test_name}' status updated to '{new_status}' successfully!")

            except json.JSONDecodeError:
                st.error("❌ JSON decoding error. Check DB format.")

        else:
            st.error(f"❌ Invalid Record ID: {record_id} or No TestStatus Found!")

        conn.close()

# ----------------------------- Audio Recording -----------------------------
def record_audio(duration=10, sample_rate=44100):
    """Records audio from the microphone and saves it as a WAV file"""
    st.write("🔴 Recording...")
    progress_bar = st.progress(0)

    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=sample_rate, input=True, frames_per_buffer=1024)
    frames = []

    for i in range(0, int(sample_rate / 1024 * duration)):
        data = stream.read(1024)
        frames.append(data)
        progress_bar.progress((i + 1) / int(sample_rate / 1024 * duration))
        time.sleep(0.001)

    stream.stop_stream()
    stream.close()
    p.terminate()

    filename = os.path.abspath(f"recordings/recording_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    wf = wave.open(filename, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(p.get_sample_size(pyaudio.paInt16))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()

    st.success(f"✅ Recording saved: {filename}")
    return filename


#  Streamlit UI
st.title("🏥 Hospital & Employee Management System with Patient Tracking")

# Sidebar Main Menu
main_menu = st.sidebar.radio("📌 Select a Section", ["Patient Management", "Employee Management", "Patient Tracking System"])

choice=None
if main_menu == "Patient Management":
    menu = ["Register Patient", "Retrieve Patient Record", "Add Visit Record", "Book Appointment", "Reminders"]
    choice = st.sidebar.selectbox("📁 Patient Management Menu", menu)

# Sidebar Menu
#menu = ["Register Patient", "Retrieve Patient Record", "Add Visit Record","Book Appointment", "Reminders", "Register Employee", "View Employee Details & Download PDF"]
#choice = st.sidebar.selectbox("Select an Option", menu)

#  Register New Patient
if choice == "Register Patient":
    st.subheader("📝 Register New Patient")
    next_hospital_id = get_next_patient_id()
    st.write(f"**Next Available Patient ID:** {next_hospital_id}")

    name = st.text_input("Full Name")
    age=st.text_input("Age")
    phone = st.text_input("Phone Number")
    address = st.text_area("Address")
    height = st.text_input("Height (cm)")
    weight = st.text_input("Weight (kg)")
    blood_pressure = st.text_input("Blood Pressure (e.g., 120/80)")
    oxygen_level=st.text_input("Oxygen Level")
    diseases = st.text_area("Existing Diseases")
    first_visit = st.date_input("First Visit Date", datetime.date.today())
    billing_details = st.text_area("Billing Details")

    if st.button("Add Patient"):
        add_patient(name, age,phone, address, height, weight, blood_pressure, diseases, first_visit, billing_details,oxygen_level)

#  Retrieve Patient Record
elif choice == "Retrieve Patient Record":
    st.subheader("🔍 Retrieve Patient Record")
    hospital_id = st.text_input("Enter Hospital ID to Search")

    if st.button("Get Patient Details"):
        record = get_patient_record(hospital_id)
        if record:
            st.write(f"**Name:** {record[1]}")
            st.write(f"**Phone:** {record[2]}")
            st.write(f"**Address:** {record[3]}")
            st.write(f"**Height:** {record[4]} cm")
            st.write(f"**Weight:** {record[5]} kg")
            st.write(f"**Blood Pressure:** {record[6]}")
            st.write(f"**Diseases:** {record[7]}")
            st.write(f"**First Visit Date:** {record[8]}")
            st.write(f"**Billing Details:** {record[9]}")
            st.write(f"**Oxygen Level:** {record[10]}")


            def get_visit_history(hospital_id):
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    query = "SELECT VisitDate, Symptoms, Temperature, OxygenLevel, BloodPressure FROM PatientVisits WHERE HospitalID = ? ORDER BY VisitDate DESC"
                    cursor.execute(query, (hospital_id,))
                    visits = cursor.fetchall()
                    conn.close()
                    return visits
                return None


            # Display Visit History
            visits = get_visit_history(hospital_id)
            if visits:
                st.subheader("🗂 Visit History")
                for visit in visits:
                    st.write(f" **Date:** {visit[0]}")
                    st.write(f" **Symptoms:** {visit[1]}")
                    st.write(f"️ **Temperature:** {visit[2]} °C")
                    st.write(f" **Oxygen Level:** {visit[3]}%")
                    st.write(f" **Blood Pressure:** {visit[4]}")
                    st.markdown("---")
        #    else:
        #        st.warning("⚠️ No visit history found for this patient.")
        else:
            st.warning("⚠️ No record found for this Hospital ID.")

#  Add Visit Record for Returning Patients
elif choice == "Add Visit Record":
    st.subheader("📌 Add Visit Record")
    hospital_id = st.text_input("Enter Patient's Hospital ID")
    visit_date = st.date_input("Visit Date", datetime.date.today())
    symptoms = st.text_area("Symptoms")
    temperature = st.text_input("Temperature (°C)")
    oxygen_level = st.text_input("Oxygen Level (%)")
    blood_pressure = st.text_input("Blood Pressure (e.g., 120/80)")

    if st.button("Add Visit"):
        add_patient_visit(hospital_id, visit_date, symptoms, temperature, oxygen_level, blood_pressure)

elif choice == "Book Appointment":
    st.header("📅 Schedule an Appointment")
    patient_id = st.text_input("Enter Patient ID:")
    patient_email = st.text_input("Enter Patient Email:")
    appointment_date = st.date_input("Select Appointment Date")

    if st.button("Book Appointment"):
        result = book_appointment(patient_id, appointment_date.strftime("%Y-%m-%d"), patient_email)
        st.success(result)

elif choice == "Reminders":
    st.header("📢 Send Appointment Reminders")
    if st.button("Send Reminder Emails"):
        send_reminders()




elif main_menu == "Employee Management":
    emp_menu = ["Register Employee", "View Employee Details & Download PDF"]
    emp_choice = st.sidebar.selectbox("📁 Employee Management Menu", emp_menu)

    if emp_choice == "Register Employee":
        st.subheader("📝 Register New Employee")
        employee_id = generate_employee_id()
        st.write(f"**Next Employee ID:** {employee_id}")
        next_employee_id = generate_employee_id()
        st.write(f"**Next Available Employee ID:** {next_employee_id}")

        full_name = st.text_input("Full Name")
        department = st.selectbox("Department", ["HR", "Technical & Support Staff", "Emergency & Surgical Staff", "Finance",
                                   "Nursing", "Pharmacy", "Administration"])
        role = st.selectbox("Role", ["Manager", "Technician", "Nurse", "Doctor", "Receptionist", "Medical Equipment Technician",
                             "Accountant", "Pharmacist"])
        contact = st.text_input("Contact")
        email = st.text_input("Email")
        salary = st.number_input("Salary", min_value=0.0, step=1000.0)
        join_date = st.date_input("Joining Date")
        shift = st.selectbox("Shift", ["Morning", "Evening", "Night"])
        status = st.selectbox("Status", ["Active", "Inactive"])

        if st.button("➕ Add Employee"):
            add_employee(full_name, department, role, contact, email, salary, join_date, shift, status)

    elif emp_choice == "View Employee Details & Download PDF":
        employee_id = st.text_input("Enter Employee ID")
        if st.button("Get Details"):
            if employee_id.strip() == "":
                st.warning("⚠️ Please enter a valid Employee ID.")
            else:
                employee_data = get_employee_details(employee_id)

                if employee_data is not None:
                    st.success("✅ Employee Found!")

                    # Display Details
                    st.write(f"**Full Name:** {employee_data['FullName']}")
                    st.write(f"**Department:** {employee_data['Department']}")
                    st.write(f"**Role:** {employee_data['Role']}")
                    st.write(f"**Contact:** {employee_data['Contact']}")
                    st.write(f"**Email:** {employee_data['Email']}")
                    st.write(f"**Salary:** ${employee_data['Salary']}")
                    st.write(f"**Joining Date:** {employee_data['JoinDate']}")
                    st.write(f"**Shift:** {employee_data['Shift']}")
                    st.write(f"**Status:** {employee_data['Status']}")

                    # Generate PDF
                    pdf_path = generate_employee_pdf(employee_data)

                    # Provide PDF Download Button
                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button(
                            label="📄 Download Employee Report (PDF)",
                            data=pdf_file,
                            file_name=f"Employee_{employee_id}.pdf",
                            mime="application/pdf"
                        )

                else:
                    st.error("❌ Employee Not Found!")

# Patient Tracking System Section
elif main_menu == "Patient Tracking System":
    page = st.sidebar.radio("📌 Patient Tracking", ["📝 Record Doctor's Notes", "📁 View Patient Records", "🔄 Update Test Status"])

    if page == "📝 Record Doctor's Notes":
        st.header("🎤 Record Doctor's Notes & Transcribe")
        patient_id = st.text_input("🆔 Patient ID")
        doctor_id = st.text_input("👨‍⚕️ Doctor ID")
        duration = st.slider("🎙 Recording Duration (seconds)", min_value=5, max_value=60, value=10)

        if st.button("🎙 Start Recording"):
            if not patient_id or not doctor_id:
                st.error("❌ Please enter both Patient ID and Doctor ID.")
            else:
                recording_file = record_audio(duration=duration)
                transcription_text, extracted_tests = transcribe_audio(recording_file)
                st.text_area("📜 Transcription:", transcription_text, height=150)
                st.write("✅ Extracted Tests:",
                         ", ".join(extracted_tests) if extracted_tests else "⚠ No tests detected.")
                save_patient_record(patient_id, doctor_id, recording_file, transcription_text, extracted_tests)

    elif page == "📁 View Patient Records":
        st.header("📂 Retrieve Patient Records")
        patient_id = st.text_input("🔍 Enter Patient ID to View Records")

        if st.button("🔍 Search"):
            records = get_patient_records(patient_id)
            if records:
                for record in records:
                    st.subheader(f"📄 Record from {record[3]}")
                    st.write(f"👨‍⚕️ **Doctor ID:** {record[2]}")
                    st.write(f"📜 **Transcript:** {record[5]}")
                    if os.path.exists(record[4]):
                        st.audio(record[4])
                    else:
                        st.warning(f"⚠ Audio file not found: {record[4]}")

                    st.write("🩺 **Test Status:**")
                    test_status = json.loads(record[7]) if record[7] else {}
                    for test_name, status in test_status.items():
                        st.write(f" - **{test_name}:** {status}")

    elif page == "🔄 Update Test Status":
        st.header("📝 Update Test Status")
        record_id = st.text_input("🔍 Enter Record ID")

        if record_id:
            try:
                record_id = int(record_id)  # Ensure it's an integer
                conn = get_db_connection()
                if conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT TestStatus FROM dbo.PatientRecords WHERE ID = ?", (record_id,))
                    row = cursor.fetchone()
                    conn.close()

                    if row and row[0]:  # Ensure data exists
                        test_status_dict = json.loads(row[0])  # Parse JSON
                        st.write("🔍 **Current Test Status:**")
                        for test, status in test_status_dict.items():
                            st.write(f" - **{test}:** {status}")

                        test_name = st.text_input("🔎 Enter Test Name to Update")
                        new_status = st.selectbox("📌 Select New Status", ["Pending", "Completed", "In Progress"])

                        if st.button("✅ Update Status"):
                            update_test_status(record_id, test_name, new_status)
                    else:
                        st.error("❌ Invalid Record ID or No Test Status Found.")
            except ValueError:
                st.error("❌ Please enter a valid numeric Record ID.")
