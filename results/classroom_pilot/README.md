# Classroom Pilot Data

Anonymized survey and quiz data from the June 4, 2026 classroom pilot at Universidad de Costa Rica (see §5 of the paper). No names, emails, or other identifying information; participant codes (`P1`, `P2`, ...) are sequential IDs assigned during anonymization, not the raw Quizizz nicknames.

- `survey_responses.csv` — post-game Likert survey, n = 25.
- `quiz_item_accuracy.csv` — per-item accuracy on the post-test quiz, n = 25.
- `quiz_participant_summary.csv` — per-participant quiz summary, n = 25.

**Quiz participant count**: the raw Quizizz export recorded 27 join records. Two of them (one a duplicate participant code, one an unrelated name) show zero questions attempted, zero session time, and an identical join timestamp a few minutes after the quiz was administered — consistent with a device joining the game PIN after the session had already ended, not a real attempt. Both are excluded from the released files and from all statistics reported in the paper, leaving n = 25 quiz-takers (matching the n = 25 survey respondents, though the two instruments are not guaranteed to be the same 25 individuals — see §5.2).
