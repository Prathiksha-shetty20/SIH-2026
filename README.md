# PLANNING-TO-EXECUTION PROGRESS INTELLIGENCE

## Intelligent Data Capture & Schedule-Linking Layer for Infrastructure Project Management

Planning-to-Execution Progress Intelligence is a prototype system developed for **Smart India Hackathon 2026 (SIH26122 – Oil India Limited)** to bridge the gap between planned L5/L6 project activities and actual execution information received from daily reports, discipline sheets, and supervisor updates.

The system is designed to help project teams capture actual progress, link field updates to planned schedule activities, identify uncertain matches, and maintain traceability of progress updates.

> The prototype supports progress tracking and schedule reconciliation using automated matching and planner review. It does not replace project planners or provide definitive project decisions.

## 1. Problem

Infrastructure projects are planned using detailed schedules containing L5/L6 activities. However, actual execution information often arrives through free-text daily reports, discipline spreadsheets, and informal supervisor updates.

The wording used in field reports may differ from the wording used in the project schedule.

For example:

```text
Field Update:
spool erection 24" PW-101 completed

Planned Activity:
Erect pipe spool 24in-PW-101
```

Manually identifying the corresponding schedule activity and updating actual progress can be time-consuming and may result in inconsistent or delayed progress data.

## 2. What the System Does

The prototype:

- Processes daily progress reports.
- Processes structured discipline sheets.
- Accepts supervisor text updates.
- Extracts activity, discipline, tag, event, date, and progress information.
- Matches field updates to planned L5/L6 activities.
- Calculates a confidence score for each match.
- Automatically links high-confidence updates.
- Sends uncertain matches to planner review.
- Updates actual activity progress.
- Validates reported progress against planned schedule dates.
- Provides explanations for matching decisions.
- Maintains an audit trail.
- Displays project progress through a Streamlit dashboard.

## 3. Input Sources

The prototype uses:

- Daily progress reports.
- Discipline progress sheets.
- Supervisor text updates.
- Planned L5/L6 project schedule.

The current prototype uses synthetic/sample project data for demonstration.

## 4. Basic Architecture

```text
Daily Reports / Discipline Sheets / Supervisor Updates
                         ↓
                 Information Extraction
                         ↓
              Activity & Event Detection
                         ↓
              L5/L6 Activity Matching
                         ↓
                 Confidence Scoring
                         ↓
          ┌─────────────┴─────────────┐
          ↓                           ↓
    High Confidence             Uncertain Match
          ↓                           ↓
      Auto Link                 Planner Review
          ↓                           ↓
          └─────────────┬─────────────┘
                        ↓
                Actual Progress Update
                        ↓
                 Schedule Validation
                        ↓
                    Audit Trail
                        ↓
                     Dashboard
```

## 5. Project Structure

```text
SIH26122-Prototype/
├── app.py
├── engine.py
├── data.py
├── requirements.txt
├── .gitignore
└── venv/
```

## 6. Installation

Install the required Python packages:

```bash
pip install -r requirements.txt
```

The prototype uses packages including:

- Streamlit
- Pandas
- NumPy
- Scikit-learn
- RapidFuzz

## 7. Running the Prototype

Run the application from the project root:

```bash
streamlit run app.py
```

The dashboard provides:

- Total events processed
- Automatically linked activities
- Planner review items
- Unmatched updates
- Processing status
- Progress by discipline
- Current actual progress
- Schedule validation alerts
- Activity matching explanations
- Audit trail

## 8. Processing Pipeline

The intended processing sequence is:

```text
Field Progress Input
        ↓
Information Extraction
        ↓
Activity Matching
        ↓
Confidence Evaluation
        ↓
Auto Link / Planner Review
        ↓
Actual Progress Update
        ↓
Schedule Validation
        ↓
Audit Trail
        ↓
Dashboard
```

The current prototype demonstrates this workflow using sample project data.

## 9. Example

Suppose a supervisor reports:

```text
Piping: spool erection 24" PW-101 completed
```

The system:

1. Identifies the update as a Piping activity.
2. Extracts the activity tag.
3. Detects the completion event.
4. Searches the planned schedule.
5. Compares the update with possible L5/L6 activities.
6. Calculates a confidence score.
7. Automatically links the activity when confidence is high.
8. Sends the update to planner review when the match is uncertain.
9. Updates actual progress.
10. Records the operation in the audit trail.

## 10. Confidence-Based Matching

The prototype produces three matching decisions:

- **Auto** — The system is sufficiently confident to link the update automatically.
- **Review** — The match is possible but requires planner confirmation.
- **Unmatched** — No reliable planned activity is identified.

For example:

```text
Field Update
     ↓
Candidate Activity
     ↓
Confidence: 53%
     ↓
Planner Review
```

## 11. Planner Review

When a match requires review, the planner can see:

- Original field report.
- Discipline.
- Event type.
- Initial confidence.
- Reason for review.
- Suggested schedule activities.
- Match confidence for candidates.

The planner can select the correct activity and confirm the match.

This provides a **human-in-the-loop** workflow.

## 12. Schedule Validation

The prototype compares reported progress with planned schedule dates.

It can identify situations such as:

```text
Actual completion is earlier than planned start.
```

or:

```text
Actual completion is later than planned end.
```

These warnings help planners identify unusual or inconsistent progress information.

## 13. Explainability

The prototype provides a reason for matching decisions.

For example:

```text
kind+tag+date agree
```

indicates that the activity type, tag, and date supported the match.

For an uncertain case:

```text
ambiguous (e.g. no tag) - planner to confirm
```

This allows planners to understand why an update was automatically linked or sent for review.

## 14. Audit Trail

Every processed update is recorded in the audit trail.

The audit trail contains:

- Timestamp
- Source
- Original field input
- Activity ID
- Event
- Event date
- Confidence
- Decision
- Warnings

This provides traceability for how field information was processed and linked to the project schedule.

## 15. Limitations

- The system is a prototype.
- The current project schedule and field reports use sample/synthetic data.
- Matching quality depends on the quality of field inputs and planned schedule descriptions.
- Ambiguous or incomplete field descriptions may require planner confirmation.
- The current prototype uses text-based supervisor updates rather than voice input.
- OCR for scanned site diaries is not currently implemented.
- Direct Primavera/MS Project integration is not currently implemented.
- LLM-based conversational interaction is not currently implemented.

## 16. Demo Flow

For the prototype demonstration:

1. Open the dashboard.
2. Process a daily progress report.
3. Show automatically matched activities.
4. Process a discipline sheet.
5. Submit a supervisor update.
6. Show an uncertain match requiring planner review.
7. Open Planner Review.
8. Confirm the correct activity.
9. Show schedule validation warnings.
10. Show updated project progress on the dashboard.
11. Open the Audit Trail to demonstrate traceability.

## 17. Testing

The prototype has been tested for the main planning-to-execution workflow.

The following components have been tested:

- Daily progress report processing.
- Discipline sheet processing.
- Supervisor text update processing.
- Activity extraction and event detection.
- L5/L6 schedule activity matching.
- Confidence-based auto-linking.
- Planner review for uncertain matches.
- Planner confirmation of reviewed activities.
- Actual progress updates.
- Schedule validation warnings.
- Explainability messages.
- Audit trail generation.
- Dashboard statistics and progress views.

Example validation flows include:

```text
High-confidence match
        ↓
Automatic linking
        ↓
Actual progress update
        ↓
Audit record
```

and:

```text
Low-confidence match
        ↓
Planner Review
        ↓
Planner selects activity
        ↓
Confirmed progress update
        ↓
Audit record
```

The prototype uses sample project schedules and synthetic field-progress inputs for demonstration.

## 18. Technology Used

- Python
- Pandas
- NumPy
- Scikit-learn
- TF-IDF
- Cosine Similarity
- RapidFuzz
- Streamlit
- Git
- GitHub

## 19. Future Enhancements

Possible future extensions include:

- LLM-based conversational time agent.
- Voice-based supervisor updates.
- OCR for scanned site diaries.
- Direct Primavera/MS Project integration.
- More advanced semantic matching.
- Central project database.
- Role-based access.
- Delay and risk prediction.
- Progress forecasting.
- Historical project knowledge and institutional memory.

## 20. SIH 2026

**Problem ID:** SIH26122

**Organization:** Oil India Limited

**Problem Area:** Infrastructure Project Management

**Focus:** Real-Time Actual Progress Tracking and Planning-to-Execution Bridge

This project was developed as a prototype for **Smart India Hackathon 2026**.

## 21. License

This project is a prototype developed for academic and hackathon purposes.
