import streamlit as st
from streamlit.components.v1 import html
import re
import hashlib
import sqlite3
from PIL import Image
import time
#pip3 install st-copy
from st_copy import copy_button


import cohere
import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
import json

import numpy as np
from pgvector.psycopg import register_vector, Bit
import psycopg2
from google import genai

import uuid
import base64
import requests
import asyncio
import random
import time
import pandas as pd

load_dotenv(verbose=True)

# Initialize Qdrant and Cohere clients
co = cohere.ClientV2(api_key=os.environ.get("COHERE_API_KEY"))
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

st.set_page_config(
    page_title="Account Management",
    page_icon="🔒",
    layout="centered",
    initial_sidebar_state="collapsed"
)

def embed(input, input_type):
    response = co.embed(texts=input, model='embed-multilingual-v3.0', input_type=input_type, embedding_types=['ubinary'])
    return [np.unpackbits(np.array(embedding, dtype=np.uint8)) for embedding in response.embeddings.ubinary]

def summarize_text(long_text):
    print("long:",long_text)

    userid = st.session_state.username
    print("userid:",userid)
    
    if "chat_summary" not in st.session_state:
        st.session_state.chat_summary = []
    
    prompt = f"次の文章をuserとassistantに分けて的確に要約してください:\n{long_text}"
    gresponse = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[prompt]
    )

    summary = gresponse.text

    #response = co.embed(
        #texts=[summary],
        #model="embed-multilingual-v3.0", 
        #input_type="search_document",
        #output_dimension=1024,
        #embedding_types=["float"],
    #)

    #embedding_str = ",".join(map(str, response.embeddings.float_[0]))

    #conn = psycopg2.connect(
        #dbname="smair",
        #user="smairuser",
        #password="smairuser",
        #host="www.ryhintl.com",
        #port=10629
    #)

    #cur = conn.cursor()
    #sql = "INSERT INTO dailog_logs (userid, content, embedding) VALUES (%s, %s, %s)"
    #cur.execute(sql, (userid, summary, f"[{embedding_str}]"))
    #conn.commit()
    #cur.close()
    #conn.close()'''

    st.session_state.chat_summary.append({"role": userid, "summary": summary})
    #st.session_state.chat_summary = summary
    print(summary)



def respond(ctype,msg):
    # セッション状態の初期化
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ユーザー入力
    qry = msg
    ctype = ctype

    #if st.button("送信") and qry:
    # データベース接続
    conn = psycopg2.connect(
        dbname="smair",
        user="smairuser",
        password="smairuser",
        host="www.ryhintl.com",
        port=10629
    )
    cur = conn.cursor()

    # クエリの埋め込み
    query_embedding = embed([qry], 'search_query')[0].tolist()

    # 類似検索（dailog_logs）
    cur.execute(
        'SELECT content, 1 - (embedding <=> %s::vector) AS similarity FROM dailog_logs WHERE (1 - (embedding <=> %s::vector)) <> 0 ORDER BY similarity ASC',
        (query_embedding, query_embedding)
    )
    proof = [row[0] for row in cur.fetchall()]

    # 類似検索（monitoring_dialog）
    cur.execute(
        'SELECT content, 1 - (embedding <=> %s::vector) AS similarity FROM monitoring_dialog WHERE (1 - (embedding <=> %s::vector)) <> 0 ORDER BY similarity ASC',
        (query_embedding, query_embedding)
    )
    vector_resp = [row[0] for row in cur.fetchall()]

    # メッセージ構築
    if ctype == "デフォルト":
        message = f"{vector_resp}に基づいて{proof}を交えながら{qry}に対する答えを正確に出力してください。"
    else:
        message = f"{vector_resp}に基づいて{proof}を交えながら{qry}に対する答えを正確に関西弁で出力してください。"

    messages = [
        {"role": "system", "content": "あなたは、優秀なアシスタントです。"},
        {"role": "user", "content": message},
    ]

    # Chatモデル呼び出し
    response = co.chat(model="command-a-03-2025", messages=messages)
    bot_message = response.message.content[0].text

    # チャット履歴に追加
    st.session_state.chat_history.append({"role": "user", "content": qry})
    st.session_state.chat_history.append({"role": "assistant", "content": bot_message})

    #print("bot:",bot_message)

    # チャット履歴の表示
    #for msg in st.session_state.chat_history:
        #with st.chat_message(msg["role"]):
            #st.markdown(msg["content"])


def inject_custom_css():
    st.markdown("""
    <style>
        .logo-container {
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 1000;
        }

        .logo-container img {
            height: 50px;
            width: auto;
        }
            
        .main {
            background-color: #f8f9fa;
        }
        .stTextInput>div>div>input, .stPassword>div>div>input {
            border-radius: 10px;
            padding: 10px;
            border: 1px solid #ced4da;
        }
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            padding: 10px;
            background-color: #4a90e2;
            color: white;
            border: none;
            font-weight: 500;
            transition: all 0.3s;
        }
        .stButton>button:hover {
            background-color: #357abd;
            color: lightyellow;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        .title {
            font-size: 1.5rem;
            font-weight: 700;
            color: #2c3e50;
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .subtitle {
            font-size: 0.1rem;
            color: #7f8c8d;
            text-align: center;
            margin-bottom: 2rem;
        }
        .card {
            background: white;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            margin-bottom: 1rem;
        }
        .success-message {
            color: #27ae60;
            text-align: center;
            margin-top: 1rem;
        }
        .error-message {
            color: #e74c3c;
            text-align: center;
            margin-top: 1rem;
        }
        .footer {
            text-align: center;
            margin-top: 2rem;
            color: #95a5a6;
            font-size: 0.5rem;
        }
        .avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            margin: 0 auto 1rem auto;
            display: block;
            object-fit: cover;
            border: 3px solid #4a90e2;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()
def init_db():
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()
def validate_username(username):
    if len(username) < 4:
        return "Username must be at least 4 characters long"
    if not re.match("^[a-zA-Z0-9_]+$", username):
        return "Username can only contain letters, numbers, and underscores"
    return None

def validate_email(email):
    if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email):
        return "Please enter a valid email address"
    return None

def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long"
    if not any(char.isdigit() for char in password):
        return "Password must contain at least one number"
    if not any(char.isupper() for char in password):
        return "Password must contain at least one uppercase letter"
    return None

def validate_phone(phone):
    if phone and not re.match(r"^\+?[0-9\s\-]+$", phone):
        return "Please enter a valid phone number"
    return None
def register_user(username, email, password, phone):
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, email))
    if c.fetchone():
        conn.close()
        return False, "Username or email already exists"
    
    hashed_pw = hash_password(password)
    c.execute(
        "INSERT INTO users (username, email, password, phone) VALUES (?, ?, ?, ?)",
        (username, email, hashed_pw, phone))
    conn.commit()
    conn.close()
    return True, "Registration successful"

def login_user(username, password):
    conn = sqlite3.connect('auth.db')
    c = conn.cursor()
    hashed_pw = hash_password(password)
    
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hashed_pw))
    user = c.fetchone()
    conn.close()
    
    if user:
        return True, user
    return False, "Invalid username or password"
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = None

def show_login_form():
    with st.container():
        #st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<div class="logo-container"><img src="https://www.ryhintl.com/images/ryhlogo/ryhlogo.png" alt="Logo"></div>', unsafe_allow_html=True)
        st.markdown('<h5 class="title">お帰りなさい！</h5>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; margin-top: 1rem; font-size: 13px;">アカウントにアクセスするにはサインインしてください</p>', unsafe_allow_html=True)
        
        with st.form("ログイン"):
            username = st.text_input("ユーザー名", placeholder="ユーザー名を入力してください")
            password = st.text_input("パスワード", type="password", placeholder="パスワードを入力してください")
            #remember_me = st.checkbox("アカウント情報を記憶")
            
            submitted = st.form_submit_button("サインイン")
            if submitted:
                username_error = validate_username(username)
                password_error = validate_password(password)
                
                if username_error:
                    st.error(username_error)
                elif password_error:
                    st.error(password_error)
                else:
                    success, result = login_user(username, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_info = {
                            "id": result[0],
                            "username": result[1],
                            "email": result[2],
                            "phone": result[4]
                        }
                        st.success("ログイン成功！")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(result)
        
        st.markdown('<p style="text-align: center; margin-top: 1rem; font-size: 10px;">アカウントをお持ちでないですか？ アカウントを作成ボタンを押して登録してください</p>', unsafe_allow_html=True)
        #st.markdown('</div>', unsafe_allow_html=True)

def show_register_form():
    with st.container():
        #st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown('<h1 class="title">アカウントを作成</h1>', unsafe_allow_html=True)
        st.markdown('<p class="subtitle">今すぐ、参加して始めましょう！</p>', unsafe_allow_html=True)
        
        with st.form("register_form"):
            username = st.text_input("ユーザー名", placeholder="ユーザー名を選択してください")
            email = st.text_input("電子メール", placeholder="メールアドレスを入力してください")
            phone = st.text_input("電話番号 (オプション)", placeholder="+81-1234567890")
            password = st.text_input("パスワード", type="password", placeholder="パスワードを入力してください")
            confirm_password = st.text_input("パスワード再確認", type="password", placeholder="パスワードを再度入力してください")
            
            submitted = st.form_submit_button("登録")
            if submitted:
                errors = []
                
                username_error = validate_username(username)
                email_error = validate_email(email)
                password_error = validate_password(password)
                phone_error = validate_phone(phone)
                
                if username_error:
                    errors.append(username_error)
                if email_error:
                    errors.append(email_error)
                if password_error:
                    errors.append(password_error)
                if phone_error:
                    errors.append(phone_error)
                if password != confirm_password:
                    errors.append("パスワードが一致しません。")
                
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    success, message = register_user(username, email, password, phone)
                    if success:
                        st.success(message)
                        time.sleep(1)
                        st.session_state.show_login = True
                        st.rerun()
                    else:
                        st.error(message)
        
        st.markdown('<p style="text-align: center; margin-top: 1rem;">Already have an account? <a href="#login">Login here</a></p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def show_dashboard():
    with st.container():
        #st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<h3 class="title">ようこそ！ {st.session_state.username} 様!</h3>', unsafe_allow_html=True)
        st.markdown('<p style="text-align: center; margin-top: 1rem; font-size: 10px;"">あなたは現在、アカウントにログインしています</p>', unsafe_allow_html=True)
        
        # User avatar placeholder
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<img src="https://ui-avatars.com/api/?name=' + st.session_state.username + '&background=4a90e2&color=fff&size=200" class="avatar">', unsafe_allow_html=True)
        
        
        #st.markdown("### Account Information")
        #user_info = st.session_state.user_info
        #st.write(f"**Username:** {user_info['username']}")
        #st.write(f"**Email:** {user_info['email']}")
        #if user_info['phone']:
            #st.write(f"**Phone:** {user_info['phone']}")
        
        with st.sidebar:
            st.markdown("### QUERY EXAMPLES")
            st.markdown("""
            - **トヨタ自動車の株を買いたいと思ってるんだけど、どう思いますか？**
            - **トヨタの株、買おかな思てんねんけど、どう思う？それと、買うときに参考にしたらええ判断材料とか基準、教えてくれへん？**
            - **トヨタ自動車の株価の上昇余地はどれくらいだと思いますか？現在の株価は¥2,508で、証券街のEPS予測（¥241.37）に対してPERは20倍です。**
            - **トヨタ自動車の過去の予測履歴があれば教えてください。**
            - **トヨタ自動車のハイブリッド自動車の販売が予想以上に好調でコスト増加が抑えられていると思われるが、過去のコストや利益率の推移を確認できますか？**
            """)

        # タブの切り替え
        tab1, tab2 = st.tabs(["ダイアログ", "ダイアログ・サマリー"], width="stretch")

        with tab1:
            st.subheader("💬 ダイアログ")
            ctype = st.selectbox("会話形式", ["デフォルト", "関西弁"])
            msg = st.text_area("クエリーを入力してください。", height=200, value="トヨタ自動車の株を買いたいと思ってるんだけど、どう思いますか？ 尚、購入のための参考にすべき判断材料や基準を教えてください")
    
            if st.button("生成", on_click=respond, args=[ctype,msg]):
                # ここに応答生成ロジックを記述（例：LLM呼び出し）
                #st.write("🔍 応答生成中...")
                #st.chat_message("assistant").write(st.session_state.chat_history)
                # チャット履歴の表示
                for msg in st.session_state.chat_history:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                        copy_button(
                            msg["content"],
                            icon='material_symbols',  # default, use 'st' as alternative
                            tooltip='コピー',  # defaults to 'Copy'
                            copied_label='コピーされました'  # defaults to 'Copied!'
                            #key='Any key',  # If omitted, a random key will be generated
                        )

        with tab2:
            st.subheader("📖 ユーザー・ダイアログを要約")
            input_summary = st.text_area("要約したいユーザー・ダイアログを入力", height=200)
    
            if st.button("要約", on_click=summarize_text, args=[input_summary]):
                # 要約処理（仮）
                for msg in st.session_state.chat_summary:
                    st.markdown("要約")
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["summary"])
                    #st.text_area("要約結果", value=st.session_state.chat_summary, height=200)

                    copy_button(
                        msg["summary"],
                        icon='material_symbols',  # default, use 'st' as alternative
                        tooltip='コピー',  # defaults to 'Copy'
                        copied_label='コピーされました'  # defaults to 'Copied!'
                        #key='Any key',  # If omitted, a random key will be generated
                    )        
        
        if st.button("ログアウト"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.user_info = None
            st.success("ログアウトに成功しました!")
            time.sleep(1)
            st.rerun()
        
        #st.markdown('</div>', unsafe_allow_html=True)


def main():
    if 'show_login' not in st.session_state:
        st.session_state.show_login = True
    
    if st.session_state.logged_in:
        show_dashboard()
    else:
        if st.session_state.show_login:
            show_login_form()
            if st.button("アカウントを作成"):
                st.session_state.show_login = False
                st.rerun()
        else:
            show_register_form()
            if st.button("ログイン画面に戻る"):
                st.session_state.show_login = True
                st.rerun()
    
    st.markdown('<p class="footer">© 2025 Fund Manager Buddy. All rights reserved.</p>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
