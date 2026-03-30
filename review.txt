Python Quiz Application — Code Review Against SPEC.md
======================================================
Reviewed files (original, pre-fix state):
  main.py  |  quiz.py  |  stats.py  |  questions.json
Spec file: SPEC.md

All line numbers refer to the ORIGINAL source (commit a2a218e),
before any fixes were applied.

──────────────────────────────────────────────────────────────────────
SPEC ACCEPTANCE CRITERIA
──────────────────────────────────────────────────────────────────────

1. [PASS] SPEC §1 — Login prompt (main.py, lines 62–87)
   The app prompts for username and password on launch.  New accounts
   are created automatically when a username is not found.

2. [PASS] SPEC §2 — Dashboard "Welcome back, <username>" (main.py, line 107)
   The dashboard correctly prints "Welcome back, {username}!" and
   offers "Start New Quiz", "View Statistics", and "Logout".

3. [PASS] SPEC §2 — Start New Quiz: number of questions + category filter
   (quiz.py, lines 347–387)
   The user is asked for a category (optional, defaults to all) and a
   question count within the available range.

4. [PASS] SPEC §3 — Questions loaded from JSON file (quiz.py, lines 30–42)
   load_questions() reads questions.json and validates the "questions"
   key.  FileNotFoundError and ValueError are both caught at the call
   site (quiz.py, lines 330–339).

5. [PASS] SPEC §3 — Category filtering (quiz.py, lines 50–57)
   filter_questions() applies a case-insensitive match; leaving the
   category blank returns all questions.

6. [PASS] SPEC §4 — Display question text and options (quiz.py, lines 193–209)
   _display_question() prints the question, numbered multiple-choice
   options, or "true / false" as appropriate.

7. [PASS] SPEC §4 — Timer defaults to 15 s, adjusted by difficulty
   (quiz.py, lines 18–23 and 153–156)
   TIMER_BY_DIFFICULTY maps easy→10 s, medium→15 s, hard→25 s.
   Questions without a difficulty field default to 15 s.

8. [PASS] SPEC §4 — Answers stored, not shown until quiz ends
   (quiz.py, lines 398–416)
   Per-question results are collected into a list and only revealed in
   _display_results() after all questions have been answered.

9. [PASS] SPEC §5 — Quiz completion: score and time displayed
   (quiz.py, lines 263–268)
   Score (n/total + percentage) and total time (m:ss) are printed.

10. [PASS] SPEC §5 — Results saved to statistics file
    (stats.py, lines 36–72; called at quiz.py line 285)
    save_quiz_result() records date, score, percentage, time, and
    per-category accuracy.

11. [PASS] SPEC §5 — Preference feedback: liked / disliked questions
    (quiz.py, lines 290–314)
    After results, each question is shown and the user can mark it
    liked, disliked, or skip.

12. [PASS] SPEC §5 — Future question selection adjusted by preference
    (quiz.py, lines 97–146)
    weighted_sample() applies 3× weight to liked questions and 0.3×
    to disliked ones.

13. [PASS] SPEC §6 — View Statistics: quiz history (stats.py, lines 97–104)
    All past quizzes are listed with date, score, and time.

14. [PASS] SPEC §6 — Average quiz score (stats.py, line 107)
    Average is computed as mean of stored percentages.

15. [PASS] SPEC §6 — Best / worst category accuracy (stats.py, lines 119–140)
    Category accuracy is aggregated across all quizzes; best and worst
    are identified and a bar chart is printed.

16. [PASS] SPEC §7 — JSON question bank format matches spec
    (questions.json)
    All five question types (multiple_choice, true_false, short_answer)
    are present with the correct keys.  Extra "difficulty" fields used
    by the timer are additive and do not violate the spec.

17. [PASS] SPEC §8 — File structure: main.py → quiz.py → stats.py
    main.py imports from quiz (run_quiz) and stats (view_statistics);
    quiz.py imports from stats (save_quiz_result).

18. [PASS] SPEC §9 — Auto-logout when terminal tab is closed
    (main.py, lines 135–149)
    SIGTERM and SIGHUP handlers call sys.exit(0), which triggers the
    atexit handler that prints the logout message.

──────────────────────────────────────────────────────────────────────
BUGS AND LOGIC ERRORS
──────────────────────────────────────────────────────────────────────

19. [FAIL] weighted_sample: floating-point default causes wrong selection
    (quiz.py, line 136)

    Code:
        chosen = 0
        for i, w in enumerate(pool_weights):
            cumulative += w
            if r <= cumulative:
                chosen = i
                break

    random.uniform(0, total_weight) can return a value that is exactly
    equal to total_weight due to IEEE-754 rounding.  When that happens,
    no iteration satisfies "r <= cumulative", the loop completes without
    breaking, and chosen remains 0 — the first question in the pool is
    always picked instead of the last.  Under uniform weights this
    systematically biases sampling toward the first question.

──────────────────────────────────────────────────────────────────────
MISSING ERROR HANDLING
──────────────────────────────────────────────────────────────────────

20. [FAIL] KeyError on malformed user record (main.py, line 73)

    Code:
        if users[username]["password"] == _hash_password(password):

    If a users.json entry is missing the "password" key (e.g., due to
    a partial write or manual editing), this raises an unhandled
    KeyError, crashing the login loop with no user-facing message.

21. [WARN] _load_users() does not catch IOError (main.py, lines 22–31)

    json.JSONDecodeError is caught and handled gracefully, but an
    IOError (e.g., permission denied) propagates unhandled and will
    crash the app before the login prompt is shown.

22. [WARN] _save_users() does not catch IOError (main.py, lines 34–37)

    A write error (disk full, permissions) will raise an unhandled
    exception, silently losing the new account that was just created.

23. [WARN] Non-atomic file writes can corrupt data on crash
    (main.py lines 36–37; stats.py lines 30–31; quiz.py lines 89–94)

    All three persistence functions open the target file in "w" mode
    and write directly.  A crash or KeyboardInterrupt mid-write
    produces a truncated, invalid JSON file with no way to recover
    the previous state.

──────────────────────────────────────────────────────────────────────
SECURITY CONCERNS
──────────────────────────────────────────────────────────────────────

24. [FAIL] Unsalted SHA-256 password hashing (main.py, lines 40–42)

    Code:
        def _hash_password(password):
            return hashlib.sha256(password.encode()).hexdigest()

    Passwords are hashed with plain SHA-256 and no salt.  Consequences:
    (a) Every user with the same password gets the same hash — a single
        lookup in a pre-computed rainbow table reveals all matching
        passwords simultaneously.
    (b) SHA-256 is a fast hash; billions of guesses per second are
        feasible on commodity hardware or a GPU.
    Should use a slow, salted KDF such as PBKDF2-HMAC-SHA256, bcrypt,
    or scrypt.

25. [FAIL] Path traversal via unsanitised username in file names
    (quiz.py, lines 66 and 79; main.py has no username validation)

    Code (quiz.py line 66):
        prefs_file = f"preferences_{username}.json"

    The username accepted at login (main.py, line 62) is only checked
    for emptiness — its characters are never validated.  A username
    such as "../etc/cron.d/evil" causes the preference files to be
    read from or written to an arbitrary path on the filesystem.
    The same pattern is repeated in save_preferences (quiz.py line 79).

26. [WARN] Password comparison is not constant-time (main.py, line 73)

    Code:
        if users[username]["password"] == _hash_password(password):

    Python's string == operator exits at the first differing byte,
    making it susceptible to timing side-channel attacks.  An attacker
    who can measure response time could, in principle, determine how
    many leading bytes of the correct hash have been guessed.  Should
    use hmac.compare_digest() for constant-time comparison.

──────────────────────────────────────────────────────────────────────
CODE QUALITY
──────────────────────────────────────────────────────────────────────

27. [WARN] Short-answer grading requires exact wording (quiz.py, lines 247–248)

    Code:
        # short_answer: exact match (case-insensitive)
        return user == correct

    The question bank has answers like "exits loop" and "__init__".
    A user typing "exits the loop" or "exit loop" would be marked wrong
    despite demonstrating correct understanding.  The spec does not
    mandate exact matching; partial/fuzzy matching or multiple accepted
    answers would be more user-friendly.

28. [WARN] Unused variable q_type assigned at the top of _display_question
    does not cause a bug here (it IS used on lines 204 and 208), but the
    function parameter name `num` shadows the built-in `num` throughout;
    no practical impact but marginally reduces readability.
    (quiz.py, line 193)
