# Medical Electronic Health Record (EHR) (`medical_ehr`)

## Overview
The Medical EHR module provides a comprehensive system for managing patient electronic health records. It allows clinicians to record detailed information about patient encounters, medical history, prescriptions, and the results of medical studies. This module is central to storing and accessing clinical data within the medical center.

## Key Features
- **Patient Demographics Extension:** Enhances `res.partner` to store EHR-specific patient data (e.g., blood type, general EHR notes) and provide easy access to all related EHR components.
- **Consultations/Encounters:** Manages records of patient consultations (`medical.consultation`), including symptoms, findings, text-based diagnosis, structured coded diagnoses, and treatment plans.
- **Medical History:**
    - **Allergies:** Records patient allergies (`medical.patient.allergy`) linked to configurable allergy types (`medical.allergy.type`).
    - **Chronic Conditions:** Tracks patient chronic conditions (`medical.patient.chronic.condition`) using standardized condition codes (`medical.condition.code`, e.g., ICD-10).
    - **Vaccinations:** Logs patient vaccinations (`medical.patient.vaccination`), linking to vaccine products.
- **Prescriptions:**
    - Manages medical prescriptions (`medical.prescription`) with detailed medication lines (`medical.prescription.line`).
    - Supports medication products (from `product.product`), dosage, frequency, duration, administration routes (`medical.medication.route`), and forms (`medical.medication.form`).
    - Includes status management for prescriptions (draft, active, expired, etc.).
    - Provides a printable PDF report for prescriptions.
- **Medical Studies:**
    - Manages different types of medical studies/tests (`medical.study.type`).
    - Records patient-specific studies (`medical.patient.study`), including report text (HTML), conclusions, status, and allows for file attachments (e.g., PDF reports, images).
- **Integrated Patient View:** EHR information (consultations, history, prescriptions, studies) is accessible directly from the patient's main form view via dedicated tabs and smart buttons.

## Models
### Core EHR Models
- `res.partner` (Extended by `patient_ehr.py`): `blood_type`, `ehr_notes`, O2M links to consultations, prescriptions, history items, studies, and computed count fields.
- `medical.consultation`: Patient encounters, diagnoses (text & coded), symptoms, treatment plan.
- `medical.prescription`: Main prescription record.
- `medical.prescription.line`: Individual medications on a prescription.
- `medical.patient.study`: Records of medical tests/studies performed.
- `medical.patient.allergy`: Patient-specific allergy records.
- `medical.patient.chronic.condition`: Patient-specific chronic conditions.
- `medical.patient.vaccination`: Patient-specific vaccination records.

### Configuration & Supporting Models
- `medical.allergy.type`: Defines types of allergens.
- `medical.condition.code`: Stores diagnosis codes (e.g., ICD-10).
- `medical.medication.route`: Defines medication administration routes.
- `medical.medication.form`: Defines medication forms (e.g., tablet, syrup).
- `medical.study.type`: Defines types of medical studies.
- `product.template` / `product.product` (Extended): Added `is_vaccine` and `is_medicament` boolean fields.

## Dependencies
- `medical_appointment`: For core patient (`res.partner` extensions like `is_patient`, `is_doctor`) and doctor information, and appointment context.
- `product`: For managing medications and vaccines as Odoo products.
- `mail`: For `mail.thread` and `mail.activity.mixin` functionalities on various EHR models.

## Configuration
After installation, some initial configuration is recommended:
1.  **Define Configuration Data (via EHR Configuration Menu):**
    - `Medical Center -> Electronic Health Records -> Configuration`:
        - `Allergy Types`: Define common allergens/types.
        - `Condition Codes`: Populate with relevant diagnosis codes (e.g., import ICD-10 subset).
        - `Medication Routes`: Define standard administration routes.
        - `Medication Forms`: Define common medication forms.
        - `Study Types`: Define types of medical studies conducted.
2.  **Configure Products:**
    - For products intended as medications, ensure the "Is a Medicament?" flag is checked on the product form.
    - For products intended as vaccines, ensure the "Is a Vaccine?" flag is checked.
3.  **Sequences:** The module auto-creates sequences for Consultations (`CONS/`), Prescriptions (`PRES/`), and Medical Studies (`STDY/`). These can be reviewed/adjusted if needed under `Settings -> Technical -> Sequences & Identifiers -> Sequences`.
4.  **User Groups:** Access rights are managed using groups from the `medical_appointment` module (`Medical / User`, `Medical / Manager`). Ensure users are assigned to the appropriate groups.

## Functional Notes
- **Creating Consultations:** Usually initiated from a patient record or appointment. Allows recording symptoms, findings, diagnoses (free-text and coded), treatment plans, and issuing prescriptions directly.
- **Managing Patient History:** Allergies, chronic conditions, and vaccinations can be added/updated directly on the patient's record via the "EHR Information" tab.
- **Issuing Prescriptions:** Can be done from a consultation or directly. Involves selecting medications, specifying dosage, route, form, frequency, and duration. Prescriptions have a lifecycle (draft, active, etc.) and can be printed.
- **Recording Medical Studies:** Study requests/results can be recorded, including HTML reports and file attachments.
- **Accessing EHR Data:** Most EHR data is centralized and accessible from the patient's main form view, providing a comprehensive overview.

## Technical Notes
- **Extensibility:** The module is designed to be extensible. New types of medical history or specific clinical data points can be added.
- **Reporting:** Includes a QWeb PDF report for prescriptions (`action_report_medical_prescription`). Further custom reports can be built on the structured data.
- **`patient_ehr.py`:** This file in `models/` contains the extensions to `res.partner` centralizing many EHR O2M links and computed fields for the patient form.

---
This README provides a guide to the Medical EHR module. For more detailed technical information, refer to the model and view definitions within the module.
