from google.cloud import storage
import os
import io
import numpy as np
import pandas as pd
import audioop
import time
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from google.cloud import speech
import stripe
import webbrowser


os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'tech0-step3-te-bd23bed77076.json'


import streamlit as st
from audio_recorder_streamlit import audio_recorder

def upload_blob_from_memory(bucket_name, contents, destination_blob_name):
    #Google cloud storageへ音声データ（Binaly）をUploadする関数
    
    #Google Cloud storageの　バケット（like フォルダ）と作成するオブジェクト（like ファイル）を指定する。
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)

    #録音データをステレオからモノラルに変換
    contents = audioop.tomono(contents, 1, 0, 1)
    
    #指定したバケット、オブジェクトにUpload
    blob.upload_from_string(contents)

    return contents


def transcript(gcs_uri):
    #Speech to textに音声データを受け渡して文字起こしデータを受け取る関数
    
    audio = speech.RecognitionAudio(uri=gcs_uri)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=48000,
        language_code="ja-JP",
    )

    operation = speech.SpeechClient().long_running_recognize(config=config, audio=audio)
    response = operation.result(timeout=90)
   
    transcript = []
    for result in response.results:
        transcript.append(result.alternatives[0].transcript)
        
    return transcript

def recorder():
    contents = audio_recorder(
        energy_threshold = (1000000000,0.0000000002), 
        pause_threshold=0.1, 
        sample_rate = 48_000,
        text="Clickして録音開始　→　"
    )

    return contents

def countdown():
    ph = st.empty()
    N = 60*5
    exit = st.button("Skipして回答")

    for secs in range(N,0,-1):
        mm, ss = secs//60, secs%60
        ph.metric("検討時間", f"{mm:02d}:{ss:02d}")

        time.sleep(1)
        
        if secs == 0:
            return 2

        if exit:
            return 2

def countdown_answer():
    ph = st.empty()
    N = 4*5

    for secs in range(N,0,-1):
        mm, ss = secs//60, secs%60
        ph.metric("回答時間", f"{mm:02d}:{ss:02d}")

        time.sleep(1)
        if secs == 1:
            text_timeout = "時間切れです。リロードして再挑戦してください"
            return text_timeout

def google_spread(list):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    json = 'tech0-step3-te-bd23bed77076.json'

    credentials = ServiceAccountCredentials.from_json_keyfile_name(json, scope)
    gc = gspread.authorize(credentials)

    SPREADSHEET_KEY = '1eXLTugi8tzy_L_keNkeu-Slyl6YbHlRJ7-WDXdNP7n4'
    worksheet = gc.open_by_key(SPREADSHEET_KEY).sheet1

    items = list

    worksheet.append_row(items)




st.title('ケース面接Quest')
st.write("ケース面接の練習ができるアプリです。")
st.text("① 設問番号を選ぶと設問文が表示されます  \n② 5分間の検討時間の後、回答（音声録音）に移行します  \n③ 回答（音声）は文字起こしされます。誤字を修正して提出してください  \n④ 数日後、現役コンサルタントのFeedbackをメールに送付します！！")

if "state" not in st.session_state:
   st.session_state["state"] = 0

if st.button("さっそくTry!"):
    st.session_state["state"] = 1

if st.session_state["state"] == 0:
    st.stop()

st.info('問題番号を選ぶと回答が始まります')
df_list = pd.read_csv("question_list.csv", header = None)
option = st.selectbox(
    '問題番号を選択してください',
    df_list[0])
question = ""
if option is not df_list[0][0]:
    question = df_list[df_list[0]==option].iloc[0,1]

if question == "":
    st.stop()

st.success('■ 設問：　' + question)

if st.session_state["state"] == 1:
    st.session_state["state"] = countdown()

contents = recorder()

if contents == None:
    st.info('①　アイコンボタンを押して回答録音　(アイコンが赤色で録音中)。  \n②　もう一度押して回答終了　(再度アイコンが黒色になれば完了)')
    timeout_msg = countdown_answer()
    st.info(timeout_msg)
    st.stop()

st.info('【録音完了！　音声分析中...】  \n　↓分析中は録音データをチェック！')
st.audio(contents)


id = str(datetime.datetime.now()).replace('.','-').replace(' ','-').replace(':','-')
bucket_name = 'tech0-speachtotext'
destination_blob_name = 'test_' + id + '.wav'
gcs_uri="gs://" + bucket_name + '/' +destination_blob_name

upload_blob_from_memory(bucket_name, contents, destination_blob_name)
transcript = transcript(gcs_uri)
text = '。\n'.join(transcript)

status = st.info('分析が完了しました！')

with st.form("form1"):
    name = st.text_input("名前/Name")
    email = st.text_input("メールアドレス/Mail address")
    answer = st.text_area("回答内容（修正可能）",text)
    fb_request = st.radio(
        "練習 or 本提出の確認",
        ("練習用です（Feedbackを希望しない）", "本提出用です（Feedbackを希望する）")
        )
    if fb_request == "練習用です（Feedbackを希望しない）":
        fb_flag = "0"
    else:
        fb_flag = "1"

    submit = st.form_submit_button("Submit")



if submit:
    if name == '':
        st.error('名前/Nameを入力してください')
    
    if email == '':
        st.error('メールアドレス/Mail addressを入力してください')

    if answer == '':
        st.error('回答内容を入力してください')

    if (name is not '' and email is not '' and answer is not ''):
        url = 'https://buy.stripe.com/test_14k28W8L71FH4PS28b'

        st.info('回答が提出されました。3秒後に決済画面に移動します。')
        st.error('※注意※  \n決済が完了しなければ、Feedbackは送付されません  \n正しいメールアドレスをご入力ください')
        list = [id, name, email, question, answer, gcs_uri, fb_flag]
        google_spread(list)

        webbrowser.open_new_tab(url)

st.stop()


