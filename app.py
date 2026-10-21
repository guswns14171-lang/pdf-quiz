import json
import streamlit as st
from google import genai
from pypdf import PdfReader

# 페이지 기본 설정
st.set_page_config(
    page_title="PDF 문제 생성기", page_icon="📚", layout="centered"
)

st.title("📚 PDF 강의 자료 문제 생성기")
st.write(
    "PDF를 업로드하면 AI가 문제를 만들고, 스마트폰이나 아이패드에서 바로 풀 수"
    " 있습니다!"
)

# 사이드바 설정 (API 키 입력)
with st.sidebar:
  st.header("⚙️ 설정")
  api_key = st.text_input("Gemini API Key", type="password")
  st.markdown("[Google AI Studio에서 API 키 발급받기](https://aistudio.google.com/)")
  st.info(
      "발급받은 Gemini API Key를 입력하면 앱을 정상적으로 사용할 수 있습니다."
  )

# PDF 파일 업로드
uploaded_file = st.file_uploader(
    "공부할 PDF 강의 자료를 업로드하세요", type=["pdf"]
)

if uploaded_file and api_key:
  client = genai.Client(api_key=api_key)

  # PDF 텍스트 추출
  with st.spinner("📄 PDF 파일 분석 중..."):
    try:
      reader = PdfReader(uploaded_file)
      text = ""
      for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
          text += extracted + "\n"
    except Exception as e:
      st.error(f"PDF를 읽는 중 오류가 발생했습니다: {e}")
      text = ""

  if text and st.button("🚀 AI 문제 생성하기"):
    with st.spinner("🤖 AI가 강의 내용을 분석하고 문제를 출제하고 있습니다..."):
      prompt = f"""
            다음 강의 텍스트를 바탕으로 핵심을 파악할 수 있는 객관식 문제 3개를 만들어주세요.
            반드시 아래 JSON 형식으로만 응답해주세요. 마크다운 백틱(```json ... ```)을 쓰지 말고 순수 JSON 문자열만 반환해주세요.
            
            [
              {{
                "question": "문제 내용",
                "options": ["1번 보기", "2번 보기", "3번 보기", "4번 보기"],
                "answer": 정답번호(1부터 4까지의 정수),
                "explanation": "상세한 해설 내용"
              }}
            ]
            
            강의 텍스트:
            {text[:10000]}
            """

      try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        res_text = response.text.strip()

        # 마크다운 태그 정제
        if res_text.startswith("```json"):
          res_text = res_text[7:]
        if res_text.startswith("```"):
          res_text = res_text[3:]
        if res_text.endswith("```"):
          res_text = res_text[:-3]

        questions = json.loads(res_text.strip())
        st.session_state["questions"] = questions
        st.success("✨ 문제가 성공적으로 생성되었습니다!")
      except Exception as e:
        st.error(f"AI 문제 생성 중 오류가 발생했습니다: {e}")

# 문제가 생성된 경우 화면에 표시
if "questions" in st.session_state:
  st.markdown("---")
  st.subheader("📝 문제 풀기")

  user_answers = {}
  for i, q in enumerate(st.session_state["questions"]):
    st.markdown(f"**문제 {i+1}. {q['question']}**")
    user_answers[i] = st.radio(
        f"보기 선택 ({i+1})", q["options"], key=f"q_{i}", index=None
    )
    st.write("")

  if st.button("📊 제출 및 채점하기"):
    score = 0
    st.markdown("---")
    st.subheader("🎯 채점 결과")
    for i, q in enumerate(st.session_state["questions"]):
      selected = user_answers.get(i)
      correct_option = q["options"][q["answer"] - 1]

      if selected == correct_option:
        score += 1
        st.success(f"문제 {i+1} 정답! 🎉\n\n> **해설**: {q['explanation']}")
      elif selected:
        st.error(
            f"문제 {i+1} 오답... (선택한 답: {selected} / 정답: "
            f"'{correct_option}')\n\n> **해설**: {q['explanation']}"
        )
      else:
        st.warning(
            f"문제 {i+1}을 풀지 않았습니다. (정답: '{correct_option}')\n\n> "
            f"**해설**: {q['explanation']}"
        )

    st.info(f"**총점: {score} / {len(st.session_state['questions'])}점**")