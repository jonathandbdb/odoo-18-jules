# Medical Patient Portal (`medical_patient_portal`)

## Overview
This module provides patients with secure access to their medical information through Odoo's web portal. Phase 1 of this portal focuses on allowing patients to view key aspects of their health records and upcoming appointments, empowering them with greater insight and access to their data.

## Key Features (Phase 1 - Viewing Information)
- **Centralized Health Records Access:** Adds a "My Health Records" section to the patient's "My Account" portal page, serving as a hub for all medical information.
- **View Appointments:** Patients can view a list of their upcoming and past medical appointments, including details like date, time, doctor, specialty, and status. The list supports pagination, sorting, and filtering.
- **View Clinical History Summary:** Provides a summary page displaying:
    - Recent consultations (date, doctor, diagnosis/reason).
    - Active chronic conditions.
    - Recorded allergies.
- **View and Download Prescriptions:** Patients can list their medical prescriptions (active, past) and download PDF copies of each prescription. A detailed view of prescription lines is also available.
- **View Medical Studies & Attachments:** Allows patients to view their medical studies (e.g., lab results, imaging reports), including study type, date, status, and conclusion. They can also securely download any attachments associated with these studies.
- **Secure Access:** Strong emphasis on data privacy through Odoo's record rule mechanism, ensuring patients can only view their own medical records.

## Key Components
- **Portal Controllers:** Python controllers (e.g., `portal_ehr.py`, `portal_appointment.py`) handle the logic for fetching and preparing patient-specific data for the portal views. These controllers manage routes like `/my/medical/appointments`, `/my/medical/history`, `/my/medical/prescriptions`, `/my/medical/studies`.
- **QWeb Templates:** XML-based QWeb templates define the structure and presentation of the portal pages, ensuring a user-friendly interface. These are located in the `views/` directory (e.g., `portal_templates_base.xml`, `portal_templates_appointments.xml`, etc.).

## Dependencies
- `portal`: Provides the core Odoo portal functionality and framework.
- `medical_appointment`: Needed for accessing and displaying patient appointment data.
- `medical_ehr`: Essential for accessing and displaying all EHR data, including consultations, medical history, prescriptions, and studies.

## Security
- **Record Rules:** The cornerstone of security for this module. `ir.rule` records are defined in `security/medical_patient_portal_security.xml` for all relevant medical models (`medical.appointment`, `medical.consultation`, `medical.prescription`, `medical.patient.study`, `medical.patient.allergy`, etc.). These rules strictly enforce that portal users can only read data linked to their own `res.partner` (patient) record.
- **Controller Checks:** Controllers that serve file downloads (e.g., prescription PDFs, study attachments) include additional checks to verify that the requested document belongs to an accessible record of the logged-in user.

## Configuration & Usage
1.  **User Setup:**
    - Ensure the patient (`res.partner`) has an associated portal user (`res.users` record with "Portal User" group). This is typically done by granting portal access from the contact form in the Odoo backend.
    - The patient's `res.partner` record must be correctly linked to this portal user.
2.  **Accessing the Portal:** Patients log in to the Odoo portal using their credentials. They will find a "My Health Records" section (or similar link) in their "My Account" area, which leads to the various medical information pages.
3.  **Record Rules:** The record rules are applied automatically upon module installation. No further configuration is typically needed for these rules unless specific customizations are desired.

## Functional Notes
- **Read-Only Access (Phase 1):** The current phase focuses on providing patients with read-only access to their information and the ability to download existing documents.
- **Navigation:** Links within the "My Health Records" section and breadcrumbs help patients navigate between different views (e.g., list of appointments, list of prescriptions).
- **Pagination & Filtering:** Lists of records (appointments, prescriptions, studies, consultations) include pagination for handling large datasets and may offer sorting and filtering options.

## Technical Notes
- **Controller Logic:** Portal controllers inherit from `odoo.addons.portal.controllers.portal.CustomerPortal` and use its helper methods (e.g., `pager`, `_prepare_portal_layout_values`, `_document_check_access`).
- **QWeb for Views:** All frontend rendering is done using QWeb templates, leveraging Bootstrap for styling as part of the standard Odoo portal.

---
This README provides a guide to Phase 1 of the Medical Patient Portal module. Future phases may include functionalities like online appointment booking.
