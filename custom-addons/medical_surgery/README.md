# Medical Surgery Management (`medical_surgery`)

## Overview
This module provides comprehensive tools for managing surgical procedures within a medical center. It covers the definition of operating rooms (ORs), management of surgical equipment types and team roles, scheduling of surgeries, assignment of surgical teams, recording of pre-operative and post-operative details, and integration with Odoo's calendar for OR booking visualization.

## Key Features
- **Operating Room Management:** Define and manage operating rooms (`medical.operating.room`), including their available equipment.
- **Surgical Equipment Types:** Maintain a list of surgical equipment types (`medical.equipment.type`) that can be associated with ORs.
- **Surgical Team Roles:** Define various roles within a surgical team (`medical.surgical_team_role` - e.g., Surgeon, Anesthetist, Scrub Nurse).
- **Surgery Scheduling:** Comprehensive `medical.surgery` model to record all details of a surgical procedure, including patient, OR, planned and actual times, primary surgeon, and other team members.
- **Surgical Team Assignment:** Link specific staff members (as `res.partner` or `hr.employee`) to surgeries with defined roles using the `medical.surgery.team_member` model.
- **Clinical Information:** Record procedure name, pre-operative and post-operative diagnoses (linking to `medical.condition.code`), operative notes, anesthesia notes, pre-operative checklist notes, and post-operative care instructions.
- **Status Tracking:** Manage the lifecycle of a surgery with statuses like Draft, Scheduled, Confirmed, In Progress, Completed, Cancelled.
- **Calendar Integration:** Automatically creates and updates `calendar.event` records for scheduled surgeries, providing a visual schedule for OR bookings. Events are linked to the surgery record and reflect key details.

## Models
### Core Models
- `medical.operating.room`: Defines operating rooms, their descriptions, and associated equipment.
- `medical.surgery`: The central model for managing all aspects of a surgical procedure.
- `medical.surgery.team_member`: Intermediate model linking personnel (`res.partner` or `hr.employee`) and their roles (`medical.surgical_team_role`) to a specific `medical.surgery`.

### Configuration & Supporting Models
- `medical.equipment.type`: Defines types of medical equipment available in ORs.
- `medical.surgical_team_role`: Defines roles that can be assigned to members of a surgical team.
- `calendar.event` (Extended implicitly): Linked via a Many2one field `calendar_event_id` on `medical.surgery`.

## Dependencies
- `medical_ehr`: For access to patient records (`res.partner` with `is_patient=True`), doctor information (`res.partner` with `is_doctor=True`), and `medical.condition.code` for diagnoses.
- `calendar`: Essential for creating and managing `calendar.event` records linked to surgeries for scheduling visualization.
- `hr`: If `hr.employee` is intended to be used for surgical team members (the current `medical.surgery.team_member` model uses `res.partner` but `hr` dependency might be included for broader staff management context or future refinement).

## Configuration
After installation, the following configurations are recommended:
1.  **Define Equipment Types:** Navigate to `Operating Room -> Configuration -> Equipment Types` to list all relevant surgical equipment types.
2.  **Define Surgical Team Roles:** Go to `Operating Room -> Configuration -> Surgical Team Roles` to define roles like "Primary Surgeon", "Assistant Surgeon", "Anesthetist", "Scrub Nurse", etc.
3.  **Define Operating Rooms:** Set up your operating rooms via `Operating Room -> Operating Rooms`. For each OR, you can assign available equipment types.
4.  **User Groups:** Access rights are initially managed using groups from the `medical_appointment` module. Ensure users involved in surgery management (schedulers, surgeons, OR managers) are in appropriate groups (`Medical / User`, `Medical / Manager`).
5.  **Sequences:** A sequence for Surgery References (`SURG/`) is automatically created. This can be reviewed under `Settings -> Technical -> Sequences & Identifiers -> Sequences`.

## Functional Notes
- **Scheduling a Surgery:** Surgeries are typically created via `Operating Room -> All Surgeries -> Create`. Key information includes patient, procedure, OR, planned start/end times, and primary surgeon.
- **Assigning Surgical Team:** In the surgery form, under the "Surgical Team" tab, members can be added along with their roles.
- **OR Schedule (Calendar View):** The `Operating Room -> OR Schedule` menu provides a calendar view of all scheduled surgeries, often color-coded by OR or another criterion. This view helps in identifying available slots and managing OR utilization.
- **Status Transitions:** The surgery form includes buttons to progress the surgery through its lifecycle (e.g., Schedule, Confirm, Start Surgery, End Surgery, Cancel). These transitions also update the linked calendar event.
- **Recording Notes:** Pre-operative, operative, anesthesia, and post-operative notes can be recorded in their respective HTML fields on the surgery form.

## Technical Notes
- **Calendar Synchronization:** The `medical.surgery` model contains logic (`_synchronize_calendar_event`, and overrides for `create`, `write`, `unlink`) to keep `calendar.event` records in sync with surgery details.
- **Team Member Model:** `medical.surgery.team_member` allows for a structured way to assign multiple team members with specific roles to a single surgery.
- **Diagnoses Link:** Pre-operative and post-operative diagnoses are linked to `medical.condition.code` from the `medical_ehr` module, allowing for structured data.

---
This README provides a guide to the Medical Surgery Management module. For detailed technical information, refer to the model and view definitions within the module.
