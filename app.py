import json
import os
from PIL import Image
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from pypdf import PdfReader

# 페이지 기본 설정
st.set_page_config(
    page_title="규은핑의 문제 생성기", page_icon="📚", layout="centered"
)

st.title("📚 규은핑의 문제 생성기!!")
st.write(
    "PDF를 업로드하면 준피티가 문제를 만듭니다. 대기할 동안 주니 생각을 해주세요..!"
)

# banner.png가 실제로 있을 때만 이미지를 띄워 에러 방지
if os.path.exists("banner.png"):
  st.image("banner.png", use_container_width=True)

# Streamlit Secrets에 키가 등록되어 있는지 확인 후 자동 로드
if "GEMINI_API_KEY" in st.secrets:
  api_key = st.secrets["GEMINI_API_KEY"]
else:
  with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("Gemini API Key", type="password")
    st.markdown(
        "[Google AI Studio에서 API 키 발급받기](https://aistudio.google.com/)"
    )
    st.info(
        "발급받은 Gemini API Key를 입력하면 앱을 정상적으로 사용할 수 있습니다."
    )

# PDF 파일 업로드
uploaded_file = st.file_uploader(
    "공부할 PDF 강의 자료를 업로드하세요", type=["pdf"]
)

if uploaded_file and api_key:
  client = genai.Client(api_key=api_key)

  # PDF 텍스트 추출 (세션에 저장)
  if "pdf_text" not in st.session_state:
    with st.spinner("📄 PDF 파일 분석 중..."):
      try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
          extracted = page.extract_text()
          if extracted:
            text += extracted + "\n"
        st.session_state["pdf_text"] = text
      except Exception as e:
        st.error(f"PDF를 읽는 중 오류가 발생했습니다: {e}")
        st.session_state["pdf_text"] = ""

  text = st.session_state.get("pdf_text", "")


  # 문제 생성 함수
  def generate_questions(num_count=10):
    with st.spinner(f"🤖 준피티가 문제를 출제하고 있습니다..."):
      limited_text = text[:3000]

      prompt = f"""
            다음 강의 텍스트를 바탕으로 핵심을 파악할 수 있는 객관식 문제 {num_count}개를 만들어주세요.
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
            {limited_text}
            """
      try:
        response = client.models.generate_content(
            model="gemini-3.8-flash",
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

        new_questions = json.loads(res_text.strip())
        if "questions" not in st.session_state:
          st.session_state["questions"] = []
        st.session_state["questions"].extend(new_questions)
        st.success(f"✨ {len(new_questions)}개의 문제가 빠르게 생성되었습니다!")
        return True
      except Exception as e:
        st.session_state["error_msg"] = str(e)
        return False


  # 최초 문제 생성 버튼 (10문제)
  if text and "questions" not in st.session_state:
    if st.button("🚀 준피티에게 문제 생성 요청하기 (10문제 다 맞으면 선물!)"):
      if generate_questions(10):
        st.rerun()

  # 에러 메시지 출력
  if "error_msg" in st.session_state:
    st.error(
        f"❌ AI 문제 생성 중 오류가 발생했습니다:\n\n"
        f"{st.session_state['error_msg']}"
    )

# 문제가 생성된 경우 화면에 표시
if "questions" in st.session_state and st.session_state["questions"]:
  st.markdown("---")
  st.subheader(f"📝 문제 풀기 (총 {len(st.session_state['questions'])}문제)")

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
    st.subheader("🎯두구두구 채점 결과")
    for i, q in enumerate(st.session_state["questions"]):
      selected = user_answers.get(i)
      correct_option = q["options"][q["answer"] - 1]

      if selected == correct_option:
        score += 1
        st.success(f"문제 {i+1} 사랑해! 🎉\n\n> **해설**: {q['explanation']}")
      elif selected:
        st.error(
            f"문제 {i+1} 시러해... (선택한 답: {selected} / 정답:"
            f" '{correct_option}')\n\n> **해설**: {q['explanation']}"
        )
      else:
        st.warning(
            f"문제 {i+1}을 풀지 않았습니다. (정답: '{correct_option}')\n\n> "
            f"**해설**: {q['explanation']}"
        )

    # 세션에 점수 저장 (공유 버튼에서 사용하기 위함)
    st.session_state["last_score"] = score
    st.session_state["total_len"] = len(st.session_state["questions"])
    st.info(
        f"**총점: {st.session_state['last_score']} /"
        f" {st.session_state['total_len']}점**"
    )

  # 채점을 완료한 경우 공유 버튼 생성
  if "last_score" in st.session_state:
    score = st.session_state["last_score"]
    total = st.session_state["total_len"]
    share_text = f"📚 [규은핑의 문제 생성기]\n✨ 나의 시험 결과: 총점 {score} / {total}점 달성! 🎉\n준피티와 함께 공부 완료!"

    st.markdown("### 📤 결과 공유하기")

    # 모바일 기기(아이폰/아이패드/갤럭시)에서 카카오톡을 포함한 공유 시트를 여는 HTML 버튼
    share_html = f"""
        <div style="display: flex; gap: 10px; justify-content: center;">
            <button onclick="shareResult()" style="background-color: #fee500; color: #191919; border: none; padding: 12px 20px; font-size: 16px; font-weight: bold; border-radius: 8px; cursor: pointer; width: 100%; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                💬 카카오톡 / SNS로 점수 공유하기
            </button>
        </div>
        <script>
        function shareResult() {{
            const text = `{share_text}`;
            if (navigator.share) {{
                navigator.share({{
                    title: '규은핑의 문제 생성기 결과',
                    text: text,
                }}).catch(() => {{}});
            }} else {{
                navigator.clipboard.writeText(text).then(() => {{
                    alert('결과가 클립보드에 복사되었습니다! 카카오톡에 붙여넣기 하세요.');
                }});
            }}
        }}
        </script>
        """
    components.html(share_html, height=60)

  st.markdown("---")
  # 추가 10문제 생성 버튼
  if uploaded_file and api_key:
    if st.button("➕ 10문제 더 만들기"):
      if generate_questions(10):
        st.rerun()
