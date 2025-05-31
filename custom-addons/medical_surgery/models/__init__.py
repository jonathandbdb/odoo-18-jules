# -*- coding: utf-8 -*-
from . import medical_operating_room
from . import medical_equipment_type
from . import medical_surgical_team_role
from . import medical_surgery_team_member # Import before medical_surgery if it's referenced directly in O2M
from . import medical_surgery
# from . import surgery_checklist # If checklist items become a model
# from . import hr_employee_extension # If extending hr.employee for surgical roles
