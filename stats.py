"""
stats.py - Statistics tracking for the Python Quiz Application.
Handles saving and displaying quiz results.
"""

import json
import os
from datetime import datetime

STATS_FILE = "stats.json"


def load_stats():
    """Load statistics from the stats file."""
    if not os.path.exists(STATS_FILE):
        return {"users": {}}
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("⚠️  Warning: Statistics file is corrupted. Starting fresh.")
        return {"users": {}}
    except IOError as e:
        raise IOError(f"Could not read statistics file: {e}")


def save_stats(stats):
    """Persist statistics to the stats file."""
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(stats, f, indent=2)
    except IOError as e:
        raise IOError(f"Could not save statistics: {e}")


def save_quiz_result(username, score, total, time_taken, results):
    """
    Append a quiz result to the statistics file.

    Args:
        username: The logged-in user's name.
        score: Number of correct answers.
        total: Total number of questions.
        time_taken: Total elapsed time in seconds.
        results: List of per-question result dicts from quiz.py.
    """
    stats = load_stats()

    if username not in stats["users"]:
        stats["users"][username] = {"quizzes": []}

    # Aggregate per-category accuracy for this quiz
    category_stats = {}
    for result in results:
        cat = result["question"].get("category", "Uncategorized")
        if cat not in category_stats:
            category_stats[cat] = {"correct": 0, "total": 0}
        category_stats[cat]["total"] += 1
        if result["correct"]:
            category_stats[cat]["correct"] += 1

    quiz_record = {
        "date": datetime.now().isoformat(),
        "score": score,
        "total": total,
        "percentage": round(score / total * 100, 1) if total > 0 else 0,
        "time_taken": round(time_taken, 1),
        "categories": category_stats,
    }

    stats["users"][username]["quizzes"].append(quiz_record)
    save_stats(stats)


def view_statistics(username):
    """Display quiz statistics for the given user."""
    print("\n" + "=" * 50)
    print(f"       STATISTICS FOR {username.upper()}")
    print("=" * 50)

    try:
        stats = load_stats()
    except IOError as e:
        print(f"❌ Error loading statistics: {e}")
        input("\nPress Enter to continue...")
        return

    user_data = stats.get("users", {}).get(username, {})
    quizzes = user_data.get("quizzes", [])

    if not quizzes:
        print("\n📭 No quiz history found. Take a quiz to see your stats!")
        input("\nPress Enter to continue...")
        return

    # Quiz history
    print(f"\n📈 QUIZ HISTORY ({len(quizzes)} quiz(zes))")
    print("─" * 50)
    for i, q in enumerate(quizzes, 1):
        date = q["date"][:10]
        print(
            f"  {i}. {date} — Score: {q['score']}/{q['total']} "
            f"({q['percentage']}%) | Time: {q['time_taken']}s"
        )

    # Average score
    avg = sum(q["percentage"] for q in quizzes) / len(quizzes)
    print(f"\n📊 AVERAGE SCORE: {avg:.1f}%")

    # Aggregate category accuracy across all quizzes
    all_categories: dict = {}
    for quiz in quizzes:
        for cat, data in quiz.get("categories", {}).items():
            if cat not in all_categories:
                all_categories[cat] = {"correct": 0, "total": 0}
            all_categories[cat]["correct"] += data["correct"]
            all_categories[cat]["total"] += data["total"]

    if all_categories:
        cat_accuracy = {
            cat: data["correct"] / data["total"] * 100
            for cat, data in all_categories.items()
            if data["total"] > 0
        }

        if cat_accuracy:
            best_cat = max(cat_accuracy, key=cat_accuracy.get)
            worst_cat = min(cat_accuracy, key=cat_accuracy.get)

            print("\n🏆 CATEGORY PERFORMANCE:")
            print("─" * 50)
            for cat, acc in sorted(
                cat_accuracy.items(), key=lambda x: x[1], reverse=True
            ):
                filled = int(acc // 10)
                bar = "█" * filled + "░" * (10 - filled)
                print(f"  {cat:<28} {bar} {acc:.1f}%")

            print(f"\n✅ Best category:  {best_cat} ({cat_accuracy[best_cat]:.1f}%)")
            print(f"❌ Worst category: {worst_cat} ({cat_accuracy[worst_cat]:.1f}%)")

    input("\nPress Enter to continue...")
