# Medical Appointment Management (Odoo Module)

## Overview

The **Medical Appointment Management** module for Odoo is designed to streamline the process of scheduling, managing, and tracking medical appointments within a healthcare facility. It provides tools for receptionists, doctors, and administrative staff to efficiently manage patient appointments, link them to relevant patient and doctor records, and integrate with Odoo's calendar for a unified view of schedules.

This module serves as a foundational piece in a larger suite of medical modules, providing core appointment functionalities that can be extended by other modules like EHR (Electronic Health Record) and Surgery Management.

## Features

*   **Patient and Doctor Management:**
    *   Leverages Odoo's `res.partner` model, extending it with specific flags (`is_patient`, `is_doctor`, `is_nurse`) to categorize contacts.
    *   Allows associating doctors with medical specialties (`medical.specialty`).
    *   Provides dedicated menu items to easily access lists of patients and doctors.
*   **Appointment Scheduling:**
    *   Create new appointments, specifying patient, doctor, date/time, and duration.
    *   Default appointment duration of 30 minutes.
    *   Domain filters on patient and doctor fields in the appointment form to ensure correct selection (e.g., only show partners marked as `is_patient`).
*   **Appointment Status Management:**
    *   Workflow for appointments: Draft -> Confirmed -> Done / Cancelled.
    *   Action buttons on the appointment form to progress through the statuses.
    *   Visual status tracking using statusbar widget and tree view decorations.
*   **Calendar Integration:**
    *   Automatically creates a `calendar.event` for each medical appointment.
    *   Synchronizes appointment details (name, start/stop times, attendees) with the calendar event.
    *   Updates or deletes the calendar event when the appointment is modified, cancelled, or deleted.
    *   Assigns the calendar event to the doctor's user (if linked) or the creating user.
*   **Communication:**
    *   Inherits `mail.thread` and `mail.activity.mixin` for appointments, allowing for communication (chatter) and activity scheduling related to appointments.
*   **Configuration:**
    *   Define medical specialties for doctors.
    *   (Future extension via `medical_schedule`): Define doctor working hours and exceptions.
*   **User Interface:**
    *   Dedicated menu structure for "Medical Center" with sub-menus for Appointments, Patients, Doctors, and Configuration.
    *   Form, tree, and calendar views for appointments.
    *   Form and tree views for patients, doctors, and specialties.
*   **Security:**
    *   Basic access rights defined for medical users and managers (using groups like `group_medical_user`, `group_medical_manager`).
    *   Module category "Medical" for organizing related applications and groups.

## Models

### Core Models
*   **`medical.appointment`**: Main model for managing appointment details, status, and links to patient, doctor, and calendar event.
*   **`medical.specialty`**: Stores different medical specialties that can be assigned to doctors.
*   **`res.partner` (Extended)**:
    *   `is_patient`: Boolean flag to identify a partner as a patient.
    *   `is_doctor`: Boolean flag to identify a partner as a doctor.
    *   `is_nurse`: Boolean flag to identify a partner as a nurse.
    *   `specialty_ids`: Many2many field on doctors linking to `medical.specialty`.
    *   `is_patient_visible`, `is_doctor_visible`, `is_nurse_visible`: Computed fields to control UI visibility of the boolean flags based on context.
*   **`medical.patient`**: (Inherits `res.partner`) Proxy model used in `medical.appointment`'s `patient_id` field to specifically refer to partners who are patients.
*   **`medical.doctor`**: (Inherits `res.partner`) Proxy model used in `medical.appointment`'s `doctor_id` field to specifically refer to partners who are doctors.

### Configuration Models
*   **`ir.module.category`**: Defines the "Medical" application category.
*   **`res.groups`**: Defines `group_medical_user` and `group_medical_manager` for access control.

## Usage

1.  **Install the Module:**
    *   Ensure the module is in your Odoo addons path.
    *   Install "Medical Appointment Management" from the Apps menu.

2.  **Configure Medical Staff:**
    *   Go to `Medical Center -> Doctors -> Create` (or edit existing Partners).
    *   Mark relevant partners as "Is a Doctor" and assign specialties.
    *   Mark relevant partners as "Is a Nurse" if applicable for other modules.
    *   Go to `Medical Center -> Configuration -> Specialties` to define available medical specialties.

3.  **Register Patients:**
    *   Go to `Medical Center -> Patients -> Create` (or edit existing Partners).
    *   Mark relevant partners as "Is a Patient".

4.  **Schedule Appointments:**
    *   Go to `Medical Center -> Appointments -> All Appointments`.
    *   Click "Create" to schedule a new appointment.
    *   Fill in the patient, doctor, date, time, and duration.
    *   The appointment will appear in the Odoo Calendar for the assigned doctor/user.

5.  **Manage Appointment Status:**
    *   Open an appointment from the list or calendar view.
    *   Use the buttons in the header (Confirm, Mark as Done, Cancel, Set to Draft) to update its status.

## Dependencies

*   **`base`**: Base Odoo module.
*   **`mail`**: For communication features (chatter, activities).
*   **`calendar`**: For calendar integration of appointments.
*   **`resource`**: (Indirect, via `medical_schedule` if that module is present and used for advanced scheduling rules, but also for `calendar.event`'s resource handling).

## Future Enhancements / Related Modules

*   **`medical_schedule`**: Manages doctor working hours, availability, and exceptions, which can be used to validate appointment slots.
*   **`medical_ehr`**: Links appointments to electronic health records, consultations, prescriptions, etc.
*   **`medical_patient_portal`**: Allows patients to view and manage their appointments via the Odoo portal.
*   **Notifications & Reminders**: Automated email/SMS reminders for upcoming appointments.
*   **Recurring Appointments**: Functionality to schedule recurring appointments.

## Technical Details

*   The module creates sequences for appointment references (though not explicitly detailed in the provided code snippets, it's a common practice).
*   The `_check_doctor_availability` constraint in `medical.appointment` (if `medical_schedule` is integrated) ensures appointments are booked within valid doctor schedules.
*   Calendar events are managed through overridden `create`, `write`, and `unlink` methods of `medical.appointment`.

This README provides a comprehensive overview of the Medical Appointment Management module. For detailed model fields and view structures, refer to the Python and XML files within the module.
