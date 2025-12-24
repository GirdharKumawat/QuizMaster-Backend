import requests
import json
import sys

# ==========================================
# CONFIGURATION
# ==========================================
BASE_URL = "http://127.0.0.1:8000/api/quizzes/"


COOKIE_NAME = "access_token" 

COOKIES = {
    "HOST": {
        COOKIE_NAME: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY2NjYyNTc4LCJpYXQiOjE3NjY1NzYxNzgsImp0aSI6IjZmOGVlMzY5OTM0NDQzYTZiYjFkNDVlM2JmMzAwODc1IiwidXNlcl9pZCI6IjY5MGRlY2E4M2M2Mjc3Y2M3MDI1YmNhYyIsImVtYWlsIjoiZ2tAZ21haWwuY29tIn0.fimyk9hWLDwwBCQXOg2G2owvtyzlVyML3XLZKXLEDMs"
    },
    "STUDENT_A": {
        COOKIE_NAME: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY2NjYyNjIwLCJpYXQiOjE3NjY1NzYyMjAsImp0aSI6IjEzNjlmYTYzYjFhOTRmZWZiNTFlYzYzN2E0YTYxMTBjIiwidXNlcl9pZCI6IjY5MGRlY2QwM2M2Mjc3Y2M3MDI1YmNhZCIsImVtYWlsIjoidXNlcjFAZ21haWwuY29tIn0.sN-OH3IFne1lxl_Tb-MHV63VMKb44jYArud1vC1eM7w"
    },
    "STRANGER": {
        COOKIE_NAME: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY2NjYyNjQzLCJpYXQiOjE3NjY1NzYyNDMsImp0aSI6IjY4MzEwZGFiMTJlMDQzZDNiNjJiMTIxOTMzMmE4NWM5IiwidXNlcl9pZCI6IjY5MzgzYzYyNzE5ZWFkZGI2NTczOTJkYiIsImVtYWlsIjoidXNlcjJAZ21haWwuY29tIn0.9OB9stzZ8AAY0kFfDPy7j-koE3hlhT3PhCaVk_0aP5A"
    }
}
# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

def log(message, status="INFO"):
    if status == "PASS":
        print(f"{Colors.OKGREEN}[PASS] {message}{Colors.ENDC}")
    elif status == "FAIL":
        print(f"{Colors.FAIL}[FAIL] {message}{Colors.ENDC}")
    elif status == "INFO":
        print(f"{Colors.HEADER}[INFO] {message}{Colors.ENDC}")

# ==========================================
# TEST SUITE
# ==========================================

def run_tests():
    # We use a session object, but we will pass specific cookies for each request
    # to simulate different users.
    session = requests.Session()
    
    # GLOBAL VARIABLES
    quiz_context = { "session_id": None }

    # ---------------------------------------------------------
    # TEST 1: Create a Quiz (Setup)
    # ---------------------------------------------------------
    log("TEST 1: Host creating a quiz")
    url = f"{BASE_URL}/create/"
    
    data = {
        "title": "Cookie Test Quiz",
        "topic": "QA",
        "difficulty": "Medium",
        "duration": 60,
        "max_participants": 2,
        "pointsPerCorrect": 10,
        "questions": [
            {"question": "Q1", "options": ["A","B","C","D"], "correct_answer": "A"}
        ]
    }
    
    # CHANGE: Using 'cookies=' instead of 'headers='
    res = session.post(url, json=data, cookies=COOKIES["HOST"])
    
    if res.status_code == 201:
        quiz_context["session_id"] = res.json().get("session_id")
        log(f"Quiz Created! Session ID: {quiz_context['session_id']}", "PASS")
    else:
        log(f"Failed to create quiz: {res.text}", "FAIL")
        sys.exit()

    session_id = quiz_context["session_id"]

    # ---------------------------------------------------------
    # TEST 2: Joining Logic
    # ---------------------------------------------------------
    log("\nTEST 2: Student joining via Cookie Auth")
    url = f"{BASE_URL}/join/"
    
    # CHANGE: Using cookies=COOKIES["STUDENT_A"]
    res = session.post(url, json={"session_id": session_id}, cookies=COOKIES["STUDENT_A"])
    
    if res.status_code == 200:
        log("Student A joined successfully", "PASS")
    else:
        log(f"Student A failed to join: {res.text}", "FAIL")

    # ---------------------------------------------------------
    # TEST 3: Unauthorized Host
    # ---------------------------------------------------------
    log("\nTEST 3: Stranger trying to START the quiz")
    url = f"{BASE_URL}/start/"
    
    # CHANGE: Using cookies=COOKIES["STRANGER"]
    res = session.post(url, json={"session_id": session_id}, cookies=COOKIES["STRANGER"])
    
    if res.status_code == 403:
        log("Stranger blocked (403 Forbidden)", "PASS")
    else:
        log(f"Stranger started the quiz! Code: {res.status_code}", "FAIL")

    # ---------------------------------------------------------
    # TEST 4: Host Starts Quiz
    # ---------------------------------------------------------
    log("\nTEST 4: Host starting the quiz")
    # CHANGE: Using cookies=COOKIES["HOST"]
    res = session.post(url, json={"session_id": session_id}, cookies=COOKIES["HOST"])
    
    if res.status_code == 200:
        log("Quiz started successfully", "PASS")
    else:
        log(f"Host failed to start quiz: {res.text}", "FAIL")

    # ---------------------------------------------------------
    # TEST 5: Submission
    # ---------------------------------------------------------
    log("\nTEST 5: Submission via Cookie")
    url = f"{BASE_URL}/submit/"
    
    payload = {"session_id": session_id, "question_index": 0, "selected_option": "A"}
    res = session.post(url, json=payload, cookies=COOKIES["STUDENT_A"])
    
    if res.status_code == 200:
        log("Submission accepted", "PASS")
    else:
        log(f"Submission failed: {res.text}", "FAIL")

if __name__ == "__main__":
    run_tests()