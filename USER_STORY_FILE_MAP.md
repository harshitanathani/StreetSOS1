# Code Evidence Map for Teacher Uploads

If your board asks for code evidence for each user story, use these files.

| User Story | Main files |
|---|---|
| US1 Registration | `templates/register.html`, `auth.py`, `database.sql` |
| US2 Login & Authentication | `templates/login.html`, `auth.py`, `decorators.py` |
| US3 Complaint Submission | `templates/complaint_form.html`, `citizen.py`, `database.sql` |
| US4 Image Upload | `services.py`, `citizen.py`, `templates/complaint_form.html` |
| US5 Map / GPS | `static/js/complaint_form.js`, `templates/complaint_form.html`, `citizen.py` |
| US6 Categories | `services.py`, `static/js/complaint_form.js`, `citizen.py` |
| US7 Severity | `services.py`, `templates/admin_dashboard.html`, `worker.py` |
| US8 Municipal Dashboard & Assignment | `admin.py`, `templates/admin_dashboard.html`, `templates/manage_workers.html` |
| US9 Status Workflow & History | `worker.py`, `citizen.py`, `templates/complaint_detail.html`, `services.py` |
| US10 SLA Escalation & Verification | `services.py`, `citizen.py`, `templates/complaint_detail.html` |
| Leaderboard & Badges | `citizen.py`, `services.py`, `templates/leaderboard.html` |
