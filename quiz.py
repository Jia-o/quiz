"""
quiz.py - Quiz execution for the Python Quiz Application.
Handles question loading, filtering, timed quiz sessions, result display,
and user preference feedback.
"""

import json
import os
import random
import select
import sys
import time

from stats import save_quiz_result

QUESTIONS_FILE = "questions.json"

# Timer durations (seconds) per difficulty level
TIMER_BY_DIFFICULTY = {
    "easy": 10,
    "medium": 15,
    "hard": 25,
}


# ---------------------------------------------------------------------------
# Question loading & filtering
# ---------------------------------------------------------------------------

def load_questions():
    """Load questions from the JSON question bank."""
    if not os.path.exists(QUESTIONS_FILE):
        raise FileNotFoundError(
            f"Question bank file '{QUESTIONS_FILE}' not found."
        )
    with open(QUESTIONS_FILE, "r") as f:
        data = json.load(f)
    if "questions" not in data:
        raise ValueError(
            "Invalid question bank format: missing 'questions' key."
        )
    return data["questions"]


def get_categories(questions):
    """Return a sorted list of unique categories."""
    return sorted(set(q.get("category", "Uncategorized") for q in questions))


def filter_questions(questions, category=None):
    """Return questions matching the given category (case-insensitive)."""
    if not category:
        return questions
    return [
        q for q in questions
        if q.get("category", "").lower() == category.lower()
    ]


# ---------------------------------------------------------------------------
# Preference-weighted sampling
# ---------------------------------------------------------------------------

def _load_preferences(username):
    """Return (liked_set, disliked_set) for the user."""
    prefs_file = f"preferences_{username}.json"
    if not os.path.exists(prefs_file):
        return set(), set()
    try:
        with open(prefs_file, "r") as f:
            prefs = json.load(f)
        return set(prefs.get("liked", [])), set(prefs.get("disliked", []))
    except (json.JSONDecodeError, IOError):
        return set(), set()


def save_preferences(username, liked, disliked):
    """Persist the user's question preferences."""
    prefs_file = f"preferences_{username}.json"
    existing_liked, existing_disliked = _load_preferences(username)

    for q in liked:
        existing_liked.add(q)
        existing_disliked.discard(q)
    for q in disliked:
        existing_disliked.add(q)
        existing_liked.discard(q)

    with open(prefs_file, "w") as f:
        json.dump(
            {"liked": list(existing_liked), "disliked": list(existing_disliked)},
            f,
            indent=2,
        )


def weighted_sample(questions, num_questions, username):
    """
    Sample *num_questions* from *questions* using preference weights.
    Liked questions are 3× more likely; disliked questions are 0.3× as likely.
    Sampling is done without replacement.
    """
    liked, disliked = _load_preferences(username)

    weights = []
    for q in questions:
        q_text = q["question"]
        if q_text in liked:
            weights.append(3.0)
        elif q_text in disliked:
            weights.append(0.3)
        else:
            weights.append(1.0)

    if num_questions >= len(questions):
        # Return all questions, ordered liked → neutral → disliked
        return sorted(
            questions,
            key=lambda q: (
                0 if q["question"] in liked else
                2 if q["question"] in disliked else
                1
            ),
        )

    selected = []
    pool = list(range(len(questions)))
    pool_weights = list(weights)

    for _ in range(num_questions):
        if not pool:
            break
        total_weight = sum(pool_weights)
        r = random.uniform(0, total_weight)
        cumulative = 0.0
        chosen = len(pool) - 1  # default to last to avoid floating-point overshoot
        for i, w in enumerate(pool_weights):
            cumulative += w
            if r <= cumulative:
                chosen = i
                break
        selected.append(questions[pool[chosen]])
        pool.pop(chosen)
        pool_weights.pop(chosen)

    return selected


# ---------------------------------------------------------------------------
# Timer-aware input
# ---------------------------------------------------------------------------

def _get_timer_duration(question):
    """Return the time limit in seconds based on question difficulty."""
    difficulty = question.get("difficulty", "medium").lower()
    return TIMER_BY_DIFFICULTY.get(difficulty, 15)


def _get_answer_with_timeout(question, time_limit):
    """
    Print an answer prompt and wait up to *time_limit* seconds for input.

    Returns:
        (answer: str | None, timed_out: bool)
    """
    q_type = question.get("type", "short_answer")
    options = question.get("options", [])

    if q_type == "multiple_choice":
        prompt = f"Your answer (1-{len(options)}): "
    elif q_type == "true_false":
        prompt = "Your answer (true/false): "
    else:
        prompt = "Your answer: "

    print(prompt, end="", flush=True)

    try:
        ready, _, _ = select.select([sys.stdin], [], [], time_limit)
        if ready:
            return sys.stdin.readline().strip(), False
        print("\n⏰ Time's up! Moving to the next question.")
        return None, True
    except (AttributeError, OSError):
        # Fallback for environments where select on stdin is unavailable
        return input(), False


# ---------------------------------------------------------------------------
# Question display
# ---------------------------------------------------------------------------

def _display_question(num, total, question, time_limit):
    q_type = question.get("type", "short_answer")
    print(f"\n{'=' * 50}")
    print(
        f"Question {num}/{total}  "
        f"[Category: {question.get('category', 'General')}]"
    )
    print(f"⏱️  Time limit: {time_limit} seconds")
    print("=" * 50)
    print(f"\n{question['question']}\n")

    if q_type == "multiple_choice":
        for i, opt in enumerate(question.get("options", []), 1):
            print(f"  {i}. {opt}")
        print()
    elif q_type == "true_false":
        print("  Options: true / false\n")


# ---------------------------------------------------------------------------
# Answer checking
# ---------------------------------------------------------------------------

def _check_answer(question, user_answer):
    """Return True if *user_answer* matches the correct answer."""
    if user_answer is None:
        return False

    q_type = question.get("type", "short_answer")
    correct = question["answer"].strip().lower()
    user = user_answer.strip().lower()

    if q_type == "multiple_choice":
        options = question.get("options", [])
        try:
            idx = int(user_answer.strip()) - 1
            if 0 <= idx < len(options):
                return options[idx].strip().lower() == correct
        except ValueError:
            pass
        # Also accept a typed-out answer
        return user == correct

    if q_type == "true_false":
        true_aliases = {"true", "t", "yes"}
        false_aliases = {"false", "f", "no"}
        if user in true_aliases:
            normalised = "true"
        elif user in false_aliases:
            normalised = "false"
        else:
            normalised = user
        return normalised == correct

    # short_answer: exact match (case-insensitive)
    return user == correct


# ---------------------------------------------------------------------------
# Results display & preference collection
# ---------------------------------------------------------------------------

def _display_results(results, total_time, username):
    """Show quiz results, save statistics, and collect preference feedback."""
    score = sum(1 for r in results if r["correct"])
    total = len(results)

    print("\n" + "=" * 50)
    print("            QUIZ COMPLETE!")
    print("=" * 50)
    percentage = score / total * 100 if total > 0 else 0
    print(f"\n📊 Score: {score}/{total} ({percentage:.1f}%)")

    minutes = int(total_time // 60)
    seconds = int(total_time % 60)
    print(f"⏱️  Total time: {minutes}m {seconds}s")

    print(f"\n{'─' * 50}")
    print("ANSWER REVIEW:")
    print("─" * 50)

    for i, result in enumerate(results, 1):
        q = result["question"]
        status = "✅" if result["correct"] else "❌"
        timeout_note = " (timed out)" if result["timed_out"] else ""
        print(f"\n{i}. {status} {q['question']}")
        print(f"   Your answer: {result['user_answer'] or 'No answer'}{timeout_note}")
        if not result["correct"]:
            print(f"   Correct answer: {q['answer']}")

    # Save statistics
    try:
        save_quiz_result(username, score, total, total_time, results)
        print("\n✅ Results saved to statistics.")
    except Exception as e:
        print(f"\n⚠️  Could not save statistics: {e}")

    # Preference feedback
    print(f"\n{'─' * 50}")
    print("QUESTION FEEDBACK:")
    print("─" * 50)
    print("Mark questions you especially liked or disliked.")
    print("This will influence question selection in future quizzes.\n")

    liked = []
    disliked = []

    for i, result in enumerate(results, 1):
        q_text = result["question"]["question"]
        print(f"{i}. {q_text}")
        pref = input("   [l]iked / [d]isliked / [s]kip (Enter = skip): ").strip().lower()
        if pref in ("l", "liked"):
            liked.append(q_text)
        elif pref in ("d", "disliked"):
            disliked.append(q_text)

    if liked or disliked:
        try:
            save_preferences(username, liked, disliked)
            print("\n✅ Preferences saved!")
        except Exception as e:
            print(f"\n⚠️  Could not save preferences: {e}")

    input("\nPress Enter to return to the dashboard...")


# ---------------------------------------------------------------------------
# Main quiz entry point
# ---------------------------------------------------------------------------

def run_quiz(username):
    """Prompt for quiz settings, run the quiz, then display results."""
    print("\n" + "=" * 50)
    print("           START NEW QUIZ")
    print("=" * 50)

    # Load questions
    try:
        all_questions = load_questions()
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        input("\nPress Enter to continue...")
        return
    except (ValueError, json.JSONDecodeError) as e:
        print(f"❌ Error reading question bank: {e}")
        input("\nPress Enter to continue...")
        return

    if not all_questions:
        print("❌ No questions found in the question bank.")
        input("\nPress Enter to continue...")
        return

    # Category selection
    categories = get_categories(all_questions)
    print("\nAvailable categories:")
    for i, cat in enumerate(categories, 1):
        print(f"  {i}. {cat}")
    print("  (Press Enter to use all categories)")

    cat_input = input("\nSelect category (number or name, or Enter for all): ").strip()
    selected_category = None

    if cat_input:
        try:
            cat_idx = int(cat_input) - 1
            if 0 <= cat_idx < len(categories):
                selected_category = categories[cat_idx]
            else:
                print("❌ Invalid category number. Using all categories.")
        except ValueError:
            matching = [c for c in categories if c.lower() == cat_input.lower()]
            if matching:
                selected_category = matching[0]
            else:
                print(f"❌ Category '{cat_input}' not found. Using all categories.")

    filtered = filter_questions(all_questions, selected_category)

    if not filtered:
        print(f"❌ No questions found for category '{selected_category}'.")
        input("\nPress Enter to continue...")
        return

    # Number of questions
    max_q = len(filtered)
    while True:
        try:
            num_str = input(f"\nHow many questions? (1-{max_q}): ").strip()
            num_questions = int(num_str)
            if 1 <= num_questions <= max_q:
                break
            print(f"❌ Please enter a number between 1 and {max_q}.")
        except ValueError:
            print("❌ Please enter a valid number.")

    # Sample questions with preference weighting
    selected_questions = weighted_sample(filtered, num_questions, username)

    print(f"\n✅ Starting quiz with {num_questions} question(s).")
    if selected_category:
        print(f"   Category: {selected_category}")
    print("\nPress Enter to begin...")
    input()

    # --- Quiz execution ---
    results = []
    quiz_start = time.time()

    for i, question in enumerate(selected_questions, 1):
        time_limit = _get_timer_duration(question)
        _display_question(i, num_questions, question, time_limit)

        q_start = time.time()
        user_answer, timed_out = _get_answer_with_timeout(question, time_limit)
        q_elapsed = time.time() - q_start

        results.append({
            "question": question,
            "user_answer": user_answer,
            "correct": _check_answer(question, user_answer),
            "timed_out": timed_out,
            "time_taken": q_elapsed,
        })

    total_time = time.time() - quiz_start
    _display_results(results, total_time, username)
