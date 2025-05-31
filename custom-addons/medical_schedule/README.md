# Medical Schedule Management (`medical_schedule`)

## Overview
This module is responsible for managing the working schedules and availability of medical staff, primarily doctors. It allows defining regular working hours, specific shifts, and exceptions like holidays or time off. This information is crucial for the appointment booking process to ensure patients can only book slots when a doctor is available.

## Key Features
- **Doctor Schedules:** Define and manage weekly or date-ranged working schedules for doctors (`medical.doctor.schedule`).
- **Working Hours:** Utilizes Odoo's standard `resource.calendar.attendance` model to specify working days (e.g., Monday to Friday) and time slots (e.g., 09:00-12:00, 14:00-17:00).
- **Schedule Exceptions:** Manage one-off unavailability periods for doctors (`medical.doctor.schedule.exception`), such as holidays, sick leave, or special assignments.
- **Timezone Aware:** Designed to work with Odoo's timezone handling, ensuring schedule checks are accurate.
- **Integration with Appointments:** The `medical_appointment` module's booking logic queries this module to validate if a requested appointment slot is within a doctor's available working time, considering both their regular schedule and any exceptions.

## Models
### Core Models
- `medical.doctor.schedule`: Stores the primary schedule information for a doctor, including the applicable date range and links to their working hour lines.
    - `attendance_ids` (One2many to `resource.calendar.attendance`): Defines the actual working days and hours within the schedule.
- `medical.doctor.schedule.exception`: Records periods when a doctor is unavailable, overriding their regular schedule (e.g., holidays, sick leave). Fields include doctor, start datetime, end datetime, and reason.
- `resource.calendar.attendance` (Extended): A field `doctor_schedule_id` (Many2one `medical.doctor.schedule`) is added to link attendance lines back to a specific doctor's schedule record.

## Dependencies
- `medical_appointment`: Requires the `medical_appointment` module for linking schedules to doctors (who are `res.partner` with `is_doctor=True`). The appointment booking logic in `medical_appointment` also depends on the availability checks provided by this module.
- `resource`: Leverages `resource.calendar.attendance` from the base `resource` module for defining working times.

## Configuration
1.  **Install Dependencies:** Ensure `medical_appointment` and `resource` modules are installed.
2.  **Create Doctor Schedules:**
    - Navigate to `Medical Center -> Schedules -> Doctor Schedules`.
    - Create a new schedule for each doctor.
    - Assign the Doctor.
    - Set a "Date From" (and optionally "Date To") for the schedule's validity.
    - In the "Working Hours" tab, add lines for each working day:
        - Specify the "Day of Week".
        - Set "Hour From" and "Hour To" (e.g., 9.0 for 9 AM, 17.5 for 5:30 PM).
3.  **Manage Schedule Exceptions:**
    - Navigate to `Medical Center -> Schedules -> Schedule Exceptions`.
    - Create records for any periods a doctor is unavailable (e.g., holidays, conferences). Specify the doctor, start datetime, and end datetime.

## Functional Notes
- **Appointment Validation:** When a user tries to book an appointment in the `medical_appointment` module, the system checks the selected doctor's schedule (from this module) for the proposed date and time. If the slot is outside working hours or falls within an exception, a validation error is raised.
- **Archiving Schedules/Exceptions:** Schedules and exceptions can be archived if no longer active using the "Archive" button on their respective forms.

## Technical Notes
- **Availability Calculation:** The core logic for determining a doctor's availability at a specific time is implemented in the `_get_combined_schedule_intervals` method within the `medical.doctor.schedule` model. This method considers all active schedules and exceptions for the doctor and handles timezone conversions.
- **Reusing Odoo Standards:** The module leverages `resource.calendar.attendance` instead of creating a custom model for working time slots, promoting consistency with Odoo's resource management.

---
This README provides a guide to the medical schedule module. For more detailed technical information, refer to the model and view definitions.
