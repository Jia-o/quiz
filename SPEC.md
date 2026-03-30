Make a python quiz app with the following properties:

1) When the app launches, it prompts user to login with username and password
2) Once login complete, it displays a dashboard saying "Welcome back, <username> with the following options:
  - Start New Quiz
  - View Statistics
2) When selecting Start New Quiz:
  - Ask
    - Number of questions
    - Category filter (optional - if left blank combine all categories)
  - Load questions from JSON file
  - Filter based on category (if selected)
3) Quiz execution
  - Display question text
  - Display options (if multiple choice)
  - Start timer (default to 15 seconds, adjust based on difficulty of question)
  - Once user submits answer, store right / wrong but do not display to user until the quiz ends 
4) Quiz Completion
  - Show:
    - Score (e.g. 7/10)
    - Time taken
  - Save results to statistics file
  - Ask user to select which problems they especially liked / didn't like. Adjust questions according to preference.
5) When selecting View Statistics, open statistics file which contains
  - Quiz scores over time
  - Average quiz score
  - Categories with best / worst accuracy
6) Question bank JSON file data format
{
 "questions": [
   {
     "question": "What keyword is used to define a function in Python?",
     "type": "multiple_choice",
     "options": ["func", "define", "def", "function"],
     "answer": "def",
     "category": "Python Basics",
   },
   {
     "question": "A list in Python is immutable.",
     "type": "true_false",
     "answer": "false",
     "category": "Data Structures",
   },
   {
     "question": "What built-in function returns the number of items in a list?",
     "type": "short_answer",
     "answer": "len",
     "category": "Python Basics",
   },
   {
     "question": "Which data type is used to store key-value pairs?",
     "type": "multiple_choice",
     "options": ["list", "tuple", "dictionary", "set"],
     "answer": "dictionary",
     "category": "Data Structures",
   },
   {
     "question": "What does the 'break' statement do?",
     "type": "short_answer",
     "answer": "exits loop",
     "category": "Control Flow",
   }
 ]
}
7) File structure and error handling
  - main.py (main entry point, login + menu selection) --> quiz.py (quiz-taking platform + result display) --> stats.py (statistics tracking)
8) Automatically logs user out when tab is closed 






