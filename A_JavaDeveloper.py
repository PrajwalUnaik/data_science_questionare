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
    # Get the base directory where the script is located
    BASE_DIR = Path(__file__).resolve().parent

    # Move up to the project root (if needed) and then access Questions_Set
    file_path = BASE_DIR / "Questions_Set" / "JavaDeveloper.xlsx"

    try:
        if not file_path.exists():
            st.error(f"Error: File '{file_path}' not found at {file_path}")
            return None
        
        df = pd.read_excel(file_path, engine='openpyxl')
        
        if df.empty:
            st.warning("The file is empty.")
            return None

        # Find the correct question column
        question_col = None
        if "Question" in df.columns:
            question_col = "Question"
        elif "Questions" in df.columns:
            question_col = "Questions"
        else:
            question_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]

        # Store questions in a DataFrame
        questions_df = pd.DataFrame()
        questions_df["Question"] = df[question_col]
        return questions_df

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
        st.session_state.quiz_duration = 50 * 60  # 50 minutes
    if 'user_name' not in st.session_state:
        st.session_state.user_name = ""
    if 'user_email' not in st.session_state:
        st.session_state.user_email = ""

def select_random_questions(questions_df, num_questions=10):
    if questions_df is None or len(questions_df) == 0:
        return None
    num_to_select = min(num_questions, len(questions_df))
    selected_indices = random.sample(range(len(questions_df)), num_to_select)
    return questions_df.iloc[selected_indices].reset_index(drop=True)

def navigate_to_question(index):
    if st.session_state.questions is not None:
        st.session_state.current_index = max(0, min(index, len(st.session_state.questions) - 1))

def save_answer(question_idx, answer):
    st.session_state.user_answers[question_idx] = answer
    st.session_state.progress = int((question_idx + 1) / len(st.session_state.questions)) * 100

def start_quiz():
    all_questions = load_questions()
    
    if all_questions is not None:
        selected_questions = select_random_questions(all_questions)
        
        if selected_questions is not None:
            # Ensure session state updates properly
            st.session_state.questions = selected_questions
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
    st.write("Thank you for taking the quiz. Please wait for further instructions.")
    st.write("We appreciate your participation and effort. Good luck!")

def assess_answer(question, answer):
    """Use OpenAI API to assess the answer"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  
            messages=[
                {
                    "role": "system",
                    "content": """
                    Analyze and assess this code to the question below. Provide:
                    1. A score from 0-10 based on accuracy and completeness

                    Format the response as:
                    Score: [score]/10
                    """
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\nAnswer: {answer}"
                }
            ]
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        return f"Assessment error: {str(e)}"

def submit_answers():
    st.session_state.quiz_started = False  # Stop the quiz
    st.session_state.quiz_completed = True  # Mark quiz as completed

    try:
        # Establish Database Connection
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Create Table with Correct Structure
        create_table_query = """
        CREATE TABLE IF NOT EXISTS Evaluated (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_name VARCHAR(255),
            user_email VARCHAR(255),
            job_role VARCHAR(255),  -- ✅ Added job_role column
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

        # Prepare Query for Inserting Data (Includes job_role as "Data Science")
        insert_query = """
        INSERT INTO Evaluated 
        (user_name, user_email, job_role, 
         Q1, Answer1, Score1, Q2, Answer2, Score2, 
         Q3, Answer3, Score3, Q4, Answer4, Score4, 
         Q5, Answer5, Score5, Q6, Answer6, Score6, 
         Q7, Answer7, Score7, Q8, Answer8, Score8, 
         Q9, Answer9, Score9, Q10, Answer10, Score10)
        VALUES (%s, %s, %s,  -- ✅ job_role added
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s, 
                %s, %s, %s, %s, %s, %s);
        """

        # Extract and Structure Data Properly
        row_data = [st.session_state.user_name, st.session_state.user_email, "Java Developer"]  # Job Role added here

        with st.spinner("🔍 Saving Your Answers..."):
            for idx in range(10):  # Ensures 10 questions are handled
                if idx in st.session_state.user_answers:
                    question = st.session_state.questions.iloc[idx]['Question']  #  Q1-Q10
                    answer = st.session_state.user_answers[idx]  # Answer1-10
                    assessment = assess_answer(question, answer)

                    # Extract score safely
                    score = None  # Default to NULL
                    try:
                        score_line = [line for line in assessment.split("\n") if "Score:" in line]
                        if score_line:
                            extracted_score = score_line[0].split("/")[0].replace("Score:", "").strip()
                            if extracted_score.isdigit():  # Ensure it's a valid number
                                score = int(extracted_score)
                    except:
                        score = None  # If extraction fails, keep NULL

                    # Append Data in Correct Order
                    row_data.extend([question, answer, score])
                else:
                    row_data.extend([None, None, None])  # If no answer, insert NULL

            # Insert into MySQL
            cursor.execute(insert_query, tuple(row_data))

        conn.commit()
        cursor.close()
        conn.close()

        st.success(" Your responses have been successfully submitted!")
        st.session_state.show_thank_you = True  #  Ensure Thank You message appears

    except Exception as e:
        st.error(f"❌ Database Error: {str(e)}")


def main():
    st.set_page_config(layout="wide")
    st.title("Java Developer Coding Test")
    initialize_session_state()

    # Show the quiz questions if the quiz has started
    if st.session_state.get('quiz_started', False):
        remaining_time = check_time_remaining()
        
        if remaining_time > 0:
            st.sidebar.header("⏳ Time Remaining")
            minutes, seconds = divmod(remaining_time, 60)
            st.sidebar.metric("", f"{minutes:02d}:{seconds:02d}")

            with st.sidebar:
                st.header("📑 Question Navigator")
                selected_page = st.radio(
                    "Jump to Question:",
                    [f"Question {i+1}" for i in range(len(st.session_state.questions))],
                    index=st.session_state.current_index
                )
                selected_index = int(selected_page.split()[1]) - 1
                navigate_to_question(selected_index)
                st.progress(st.session_state.progress)
                st.info("Save your answer before navigating!")

            current_q_idx = st.session_state.current_index
            total_questions = len(st.session_state.questions)

            st.markdown(f"###  Question {current_q_idx + 1} of {total_questions}")
            question = st.session_state.questions.iloc[current_q_idx]['Question']
            st.markdown(f"<div style='font-size: 20px; margin-bottom: 20px;'>{question}</div>", unsafe_allow_html=True)

            current_answer = st.session_state.user_answers.get(current_q_idx, "")
            user_answer = st.text_area("Your Answer:", value=current_answer, height=150, key=f"answer_{current_q_idx}")

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if current_q_idx > 0:
                    if st.button("⬅️ Previous", use_container_width=True):
                        save_answer(current_q_idx, user_answer)
                        navigate_to_question(current_q_idx - 1)
            with col2:
                if current_q_idx < total_questions - 1:
                    if st.button("➡️ Next", use_container_width=True):
                        save_answer(current_q_idx, user_answer)
                        navigate_to_question(current_q_idx + 1)
                else:
                    if st.button("Submit Quiz", type="primary", use_container_width=True):
                        save_answer(current_q_idx, user_answer)
                        submit_answers()
            with col3:
                if st.button("💾Save Progress", use_container_width=True):
                    save_answer(current_q_idx, user_answer)
                    st.toast("Progress saved!")
        return  # Stop execution if quiz is in progress

    # If the quiz is completed, show the Thank You message
    if st.session_state.get('quiz_completed', False):
        show_final_message()
        return  # Stop execution to prevent form reload

    # Initial State: Show the Start Quiz form
    st.markdown("""
    <div style='border: 2px solid #4CAF50; padding: 20px; border-radius: 10px;'>
        <h3 style='color: #4CAF50;'>📝 Quiz Instructions</h3>
        <ul>
            <li>50-minute time limit</li>
            <li>10 randomly selected questions</li>
            <li>AI-powered automatic assessment</li>
            <li>Save your progress anytime</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Please enter your details to start the quiz:")
    name = st.text_input("Name:")
    email = st.text_input("Email:")

    if st.button("▶Start Quiz", type="primary"):
        if name and email:
            st.session_state.user_name = name
            st.session_state.user_email = email
            st.success(f"Welcome, {st.session_state.user_name}! Your email is {st.session_state.user_email}.")
            start_quiz()
        else:
            st.error("Please enter both your name and email to start the quiz.")

if __name__ == "__main__":
    main()