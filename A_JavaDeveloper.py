import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
import openai
from pathlib import Path
import mysql.connector
from mysql.connector import Error

# Configure OpenAI API using Streamlit Secrets
OPENAI_API_KEYY = st.secrets["OPENAI_API_KEYY"]
openai.api_key = OPENAI_API_KEYY

# Database connection parameters using Streamlit Secrets
DB_CONFIG = {
    "host": st.secrets["DB_HOST"],
    "user": st.secrets["DB_USER"],
    "password": st.secrets["DB_PASSWORD"],
    "database": st.secrets["DB_NAME"]
}

def load_questions():
    BASE_DIR = Path(__file__).resolve().parent
    file_path = BASE_DIR / "Questions_Set" / "JavaDeveloper.xlsx"

    try:
        if not file_path.exists():
            st.error(f"Error: File '{file_path}' not found at {file_path}")
            return None
        
        df = pd.read_excel(file_path, engine='openpyxl')
        
        if df.empty:
            st.warning("The file is empty.")
            return None

        question_col = "Question" if "Question" in df.columns else df.columns[0]
        return pd.DataFrame({"Question": df[question_col]})

    except Exception as e:
        st.error(f"Error loading the file: {str(e)}")
        return None

def initialize_session_state():
    if 'questions' not in st.session_state:
        st.session_state.questions = None
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'user_answers' not in st.session_state:
        st.session_state.user_answers = {}
    if 'quiz_started' not in st.session_state:
        st.session_state.quiz_started = False
    if 'progress' not in st.session_state:
        st.session_state.progress = 0
    if 'start_time' not in st.session_state:
        st.session_state.start_time = time.time()
    if 'quiz_duration' not in st.session_state:
        st.session_state.quiz_duration = 50 * 60  
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'user_email' not in st.session_state:
        st.session_state.user_email = ""

def select_random_questions(questions_df, num_questions=10):
    if questions_df is None or questions_df.empty:
        return None
    return questions_df.sample(min(num_questions, len(questions_df))).reset_index(drop=True)

def navigate_to_question(index):
    st.session_state.current_index = max(0, min(index, len(st.session_state.questions) - 1))

def save_answer(question_idx, answer):
    st.session_state.user_answers[question_idx] = answer
    st.session_state.progress = int(((question_idx + 1) / len(st.session_state.questions)) * 100)
    st.toast("Progress saved!")
    st.rerun()

def start_quiz():
    all_questions = load_questions()
    
    if all_questions is not None:
        st.session_state.questions = select_random_questions(all_questions)
        st.session_state.current_index = 0
        st.session_state.user_answers = {}
        st.session_state.quiz_started = True  
        st.session_state.progress = 0
        st.session_state.start_time = time.time()
        st.rerun()

def check_time_remaining():
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = st.session_state.quiz_duration - elapsed_time
    if remaining_time <= 0:
        st.session_state.quiz_started = False
        st.warning("⏳ Time's up! The quiz is now over.")
        show_quiz_done()
        return 0
    return int(remaining_time)

def show_quiz_done():
    st.session_state.questions = None
    st.session_state.current_index = 0
    st.session_state.quiz_completed = True

def show_final_message():
    st.title("✅ Quiz Successfully Completed!")
    st.write("Thank you for taking the quiz. Your responses have been recorded.")

def assess_answer(question, answer):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  
            messages=[
                {"role": "system", "content": "Evaluate the following answer and provide a score (0-10)."},
                {"role": "user", "content": f"Question: {question}\nAnswer: {answer}"}
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Assessment error: {str(e)}"

def submit_answers():
    st.session_state.quiz_started = False  
    st.session_state.quiz_completed = True  

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        create_table_query = """
        CREATE TABLE IF NOT EXISTS Evaluated (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_name VARCHAR(255),
            user_email VARCHAR(255),
            job_role VARCHAR(255),
            Q1 TEXT, Answer1 TEXT, Score1 INT,
            Q2 TEXT, Answer2 TEXT, Score2 INT,
            Q3 TEXT, Answer3 TEXT, Score3 INT,
            Q4 TEXT, Answer4 TEXT, Score4 INT,
            Q5 TEXT, Answer5 TEXT, Score5 INT,
            Q6 TEXT, Answer6 TEXT, Score6 INT,
            Q7 TEXT, Answer7 TEXT, Score7 INT,
            Q8 TEXT, Answer8 TEXT, Score8 INT,
            Q9 TEXT, Answer9 TEXT, Score9 INT,
            Q10 TEXT, Answer10 TEXT, Score10 INT,
            submission_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
        conn.commit()  

        insert_query = """
        INSERT INTO Evaluated 
        (user_name, user_email, job_role, 
         Q1, Answer1, Score1, Q2, Answer2, Score2, 
         Q3, Answer3, Score3, Q4, Answer4, Score4, 
         Q5, Answer5, Score5, Q6, Answer6, Score6, 
         Q7, Answer7, Score7, Q8, Answer8, Score8, 
         Q9, Answer9, Score9, Q10, Answer10, Score10)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """

        row_data = [st.session_state.user_name, st.session_state.user_email, "Java Developer"]
        
        for idx in range(10):
            question = st.session_state.questions.iloc[idx]['Question']
            answer = st.session_state.user_answers.get(idx, "")
            score = int(assess_answer(question, answer).split("/")[0].replace("Score:", "").strip()) if answer else None
            row_data.extend([question, answer, score])

        cursor.execute(insert_query, tuple(row_data))
        conn.commit()

        cursor.close()
        conn.close()
        st.success("✅ Your responses have been successfully submitted!")

    except Error as db_error:
        st.error(f"❌ Database Error: {str(db_error)}")
    except Exception as e:
        st.error(f"❌ Unexpected Error: {str(e)}")

def main():
    st.set_page_config(layout="wide")
    st.title("Java Developer Coding Test")
    initialize_session_state()

    if st.session_state.get('quiz_started', False):
        remaining_time = check_time_remaining()
        if remaining_time > 0:
            st.sidebar.header("⏳ Time Remaining")
            st.sidebar.metric("", f"{remaining_time // 60:02d}:{remaining_time % 60:02d}")

            st.write(f"### Question {st.session_state.current_index + 1}")
            question = st.session_state.questions.iloc[st.session_state.current_index]['Question']
            st.write(question)
            user_answer = st.text_area("Your Answer:", key="answer_input")
            
            if st.button("Save Answer"):
                save_answer(st.session_state.current_index, user_answer)

    else:
        st.subheader("Enter Details to Start Quiz")
        name = st.text_input("Name:")
        email = st.text_input("Email:")
        if st.button("Start Quiz") and name and email:
            st.session_state.user_name, st.session_state.user_email = name, email
            start_quiz()

if __name__ == "__main__":
    main()
