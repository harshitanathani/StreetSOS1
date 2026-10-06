# StreetSOS Testing Checklist

Use this sheet to demonstrate the user stories to your teacher.

## US1 – Registration
- Valid name/email/password creates a citizen in MySQL.
- Duplicate email is rejected.
- Invalid email is rejected.
- Password shorter than 6 characters is rejected.
- Mismatched passwords are rejected.

## US2 – Login & Authentication
- Correct credentials create a session and open the role dashboard.
- Wrong password is rejected.
- Logged-out users cannot access protected dashboards.
- Logout clears the session.

## US3 – Complaint Submission
- Complete form saves complaint and generates `SOS-...` public ID.
- Missing category / issue type / area / description / map pin is rejected.
- Complaint appears on citizen dashboard.

## US4 – Image Upload
- Valid PNG/JPG/JPEG/WEBP under 5 MB is stored.
- Unsupported extension is rejected.
- Fake/non-image file with image extension is rejected by Pillow.
- Upload above 5 MB receives the 413 page.

## US5 – Map / GPS
- Tap map places a marker.
- GPS button selects browser location when permission is available.
- Coordinates are saved in MySQL.
- Complaint detail opens the saved location in OpenStreetMap.

## US6 – Categories
- Road, Garbage, Drainage, Lighting are available.
- Issue-type options change with category.
- Invalid category/issue pair is rejected server-side.
- Category is stored with complaint.

## US7 – Severity / Priority
- Severity is calculated automatically.
- Road + Pothole + Highway scores higher than Lighting + Broken Streetlight + Residential Area.
- Admin/worker queues order escalated/high-score issues first.
- Severity score and label are visible on dashboards.

## US8 – Municipal Dashboard / Assignment
- Admin can search/filter complaints.
- Admin can create worker accounts and departments.
- Admin can assign matching department or General workers.
- Invalid department assignment is rejected.

## US9 – Status Workflow
- Report starts as Reported.
- Admin assignment changes Reported → Assigned.
- Worker changes Assigned → In Progress.
- Worker changes In Progress → Resolved with resolution note.
- Citizen changes Resolved → Verified.
- Timeline displays each transition and actor.

## US10 – SLA / Escalation / Verification
- SLA deadline is exactly 48 hours from report creation.
- Scheduler scans once per minute.
- Overdue unresolved complaints become escalated.
- Escalation is displayed to citizen/admin/worker and logged in timeline.
- Citizen can verify a resolved complaint.

## Final backlog feature – Leaderboard & Badges
- Only Verified complaints count.
- Leaderboard ranks citizens by verified complaint count.
- Badges: Civic Starter (1), Neighbourhood Helper (3), Street Guardian (5), Road Warrior (10).
